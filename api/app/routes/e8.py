"""Essential Eight assessment: one living assessment per organisation, snapshotted on completion.

Members and above answer; admins set the target level and complete (snapshot) the assessment;
auditors read. Everything below runs with app.org_id set, so RLS scopes every query.
"""

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from ..deps import OrgCaller, org_member
from ..e8 import content
from ..e8.scoring import action_plan, score
from ..models import E8AnswerRow, E8Assessment, E8Snapshot, Role, User
from ..schemas import (
    E8AnswerIn, E8AnswerOut, E8Content, E8Plan, E8PlanItem, E8RequirementOut, E8Score,
    E8SnapshotDetail, E8SnapshotSummary, E8StrategyOut, E8TargetIn,
)
from ..schemas import E8Assessment as E8AssessmentOut

router = APIRouter(prefix="/api")

# Public, tenant-free and fixed for the life of the process
CONTENT = E8Content(
    version=content.VERSION,
    attribution=content.ATTRIBUTION,
    source_url=content.SOURCE_URL,
    licence_url=content.LICENCE_URL,
    strategies=[E8StrategyOut(**asdict(s)) for s in content.STRATEGIES],
    requirements=[E8RequirementOut(**asdict(r)) for r in content.REQUIREMENTS],
)


@router.get("/e8/content", response_model=E8Content)
def get_content():
    return CONTENT


def _target_level(ctx: OrgCaller) -> int:
    return ctx.session.scalar(select(E8Assessment.target_level)) or 1


def _answers(ctx: OrgCaller) -> list[E8AnswerOut]:
    rows = ctx.session.execute(
        select(E8AnswerRow, User.name)
        .outerjoin(User, User.id == E8AnswerRow.answered_by)  # RLS hides users who left the org
        .order_by(E8AnswerRow.key)
    ).all()
    return [
        E8AnswerOut(key=a.key, answer=a.answer, note=a.note, answered_by=name, answered_at=a.answered_at)
        for a, name in rows
    ]


def _summary(snapshot: E8Snapshot, created_by: str | None) -> dict:
    return dict(
        id=snapshot.id, content_version=snapshot.content_version, target_level=snapshot.target_level,
        overall_level=snapshot.overall_level, score=snapshot.score, created_by=created_by,
        created_at=snapshot.created_at,
    )


def _snapshots():
    return (
        select(E8Snapshot, User.name)
        .outerjoin(User, User.id == E8Snapshot.created_by)
        .order_by(E8Snapshot.created_at.desc(), E8Snapshot.id.desc())
    )


@router.get("/orgs/{org_id}/e8", response_model=E8AssessmentOut)
def get_assessment(ctx: OrgCaller = Depends(org_member)):
    answers = _answers(ctx)
    last = ctx.session.execute(_snapshots().limit(1)).first()
    return E8AssessmentOut(
        content_version=content.VERSION,
        target_level=_target_level(ctx),
        answers=answers,
        score=E8Score.model_validate(asdict(score({a.key: a.answer.value for a in answers}))),
        last_snapshot=E8SnapshotSummary(**_summary(*last)) if last else None,
    )


@router.patch("/orgs/{org_id}/e8", response_model=E8AssessmentOut)
def set_target(body: E8TargetIn, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.admin)
    ctx.session.execute(
        insert(E8Assessment)
        .values(org_id=ctx.org_id, target_level=body.target_level, updated_by=ctx.user.id)
        .on_conflict_do_update(
            index_elements=[E8Assessment.org_id],
            set_={"target_level": body.target_level, "updated_by": ctx.user.id, "updated_at": func.now()},
        )
    )
    return get_assessment(ctx)


def _known_key(key: str) -> str:
    if key not in content.KEYS:
        raise HTTPException(404, "unknown requirement")
    return key


@router.put("/orgs/{org_id}/e8/answers/{key}", response_model=E8AnswerOut)
def put_answer(key: str, body: E8AnswerIn, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.member)
    values = {"answer": body.answer, "note": body.note.strip(), "answered_by": ctx.user.id}
    row = ctx.session.scalars(
        insert(E8AnswerRow)
        .values(org_id=ctx.org_id, key=_known_key(key), **values)
        .on_conflict_do_update(
            index_elements=[E8AnswerRow.org_id, E8AnswerRow.key], set_={**values, "answered_at": func.now()}
        )
        .returning(E8AnswerRow)
    ).one()
    return E8AnswerOut(key=row.key, answer=row.answer, note=row.note, answered_by=ctx.user.name,
                       answered_at=row.answered_at)


@router.delete("/orgs/{org_id}/e8/answers/{key}", status_code=204)
def clear_answer(key: str, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.member)
    ctx.session.execute(delete(E8AnswerRow).where(E8AnswerRow.key == _known_key(key)))


@router.get("/orgs/{org_id}/e8/plan", response_model=E8Plan)
def get_plan(ctx: OrgCaller = Depends(org_member)):
    target = _target_level(ctx)
    answers = {a.key: a.answer.value for a in ctx.session.scalars(select(E8AnswerRow))}
    return E8Plan(target_level=target, items=[E8PlanItem(**asdict(i)) for i in action_plan(answers, target)])


@router.post("/orgs/{org_id}/e8/snapshots", response_model=E8SnapshotDetail, status_code=201)
def complete(ctx: OrgCaller = Depends(org_member)):
    """Freeze the current answers and score."""
    ctx.require(Role.admin)
    rows = ctx.session.scalars(select(E8AnswerRow)).all()
    if not rows:
        raise HTTPException(409, "answer at least one question before completing the assessment")
    result = score({a.key: a.answer.value for a in rows})
    snapshot = E8Snapshot(
        org_id=ctx.org_id,
        content_version=content.VERSION,
        target_level=_target_level(ctx),
        overall_level=result.overall_level,
        score=asdict(result),
        answers={a.key: {"answer": a.answer.value, "note": a.note} for a in rows},
        created_by=ctx.user.id,
    )
    ctx.session.add(snapshot)
    ctx.session.flush()
    ctx.session.refresh(snapshot)
    return E8SnapshotDetail(**_summary(snapshot, ctx.user.name), answers=snapshot.answers)


@router.get("/orgs/{org_id}/e8/snapshots", response_model=list[E8SnapshotSummary])
def list_snapshots(ctx: OrgCaller = Depends(org_member)):
    return [E8SnapshotSummary(**_summary(s, name)) for s, name in ctx.session.execute(_snapshots().limit(100))]


@router.get("/orgs/{org_id}/e8/snapshots/{snapshot_id}", response_model=E8SnapshotDetail)
def get_snapshot(snapshot_id: uuid.UUID, ctx: OrgCaller = Depends(org_member)):
    row = ctx.session.execute(_snapshots().where(E8Snapshot.id == snapshot_id)).first()
    if row is None:
        raise HTTPException(404, "snapshot not found")
    return E8SnapshotDetail(**_summary(*row), answers=row[0].answers)
