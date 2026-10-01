import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..deps import Caller, OrgCaller, caller, org_member
from ..db import set_context
from ..models import Membership, Organisation, Role, User, new_id
from ..schemas import Me, MemberOut, OrgDetail, OrgIn, OrgOut, OrgSummary, RoleIn

router = APIRouter(prefix="/api")


@router.get("/me", response_model=Me)
def me(me: Caller = Depends(caller)):
    rows = me.session.execute(
        select(Organisation.id, Organisation.name, Membership.role)
        .join(Membership, Membership.org_id == Organisation.id)
        .where(Membership.user_id == me.user.id)
        .order_by(Organisation.name)
    ).all()
    return Me(
        id=me.user.id,
        email=me.user.email,
        name=me.user.name,
        organisations=[OrgSummary(id=i, name=n, role=r) for i, n, r in rows],
    )


@router.post("/orgs", response_model=OrgDetail, status_code=201)
def create_org(body: OrgIn, me: Caller = Depends(caller)):
    org_id = new_id()
    set_context(me.session, org_id=org_id)
    org = Organisation(id=org_id, name=body.name.strip(), abn=body.abn, created_by=me.user.id)
    me.session.add(org)
    me.session.flush()
    me.session.add(Membership(org_id=org_id, user_id=me.user.id, role=Role.owner))
    me.session.flush()
    me.session.refresh(org)
    return OrgDetail(**OrgOut.model_validate(org).model_dump(), role=Role.owner)


@router.get("/orgs/{org_id}", response_model=OrgDetail)
def get_org(ctx: OrgCaller = Depends(org_member)):
    org = ctx.session.get(Organisation, ctx.org_id)
    return OrgDetail(**OrgOut.model_validate(org).model_dump(), role=ctx.role)


@router.patch("/orgs/{org_id}", response_model=OrgDetail)
def update_org(body: OrgIn, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.admin)
    org = ctx.session.get(Organisation, ctx.org_id)
    org.name, org.abn = body.name.strip(), body.abn
    ctx.session.flush()
    return OrgDetail(**OrgOut.model_validate(org).model_dump(), role=ctx.role)


@router.get("/orgs/{org_id}/members", response_model=list[MemberOut])
def list_members(ctx: OrgCaller = Depends(org_member)):
    rows = ctx.session.execute(
        select(User.id, User.email, User.name, Membership.role, Membership.created_at)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == ctx.org_id)
        .order_by(Membership.created_at)
    ).all()
    return [MemberOut(user_id=i, email=e, name=n, role=r, joined_at=j) for i, e, n, r, j in rows]


def _owner_count(ctx: OrgCaller) -> int:
    return ctx.session.scalar(
        select(func.count()).where(Membership.org_id == ctx.org_id, Membership.role == Role.owner)
    )


def _membership(ctx: OrgCaller, user_id: uuid.UUID) -> Membership:
    m = ctx.session.get(Membership, (ctx.org_id, user_id))
    if m is None:
        raise HTTPException(404, "member not found")
    return m


@router.patch("/orgs/{org_id}/members/{user_id}", response_model=MemberOut)
def change_role(user_id: uuid.UUID, body: RoleIn, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.admin)
    m = _membership(ctx, user_id)
    if Role.owner in (m.role, body.role) and ctx.role != Role.owner:
        raise HTTPException(403, "only owners can grant or change the owner role")
    if m.role == Role.owner and body.role != Role.owner and _owner_count(ctx) == 1:
        raise HTTPException(409, "an organisation needs at least one owner")
    m.role = body.role
    ctx.session.flush()
    user = ctx.session.get(User, user_id)
    return MemberOut(user_id=user.id, email=user.email, name=user.name, role=m.role, joined_at=m.created_at)


@router.delete("/orgs/{org_id}/members/{user_id}", status_code=204)
def remove_member(user_id: uuid.UUID, ctx: OrgCaller = Depends(org_member)):
    """Admins remove others; anyone can remove themselves (leave)."""
    if user_id != ctx.user.id:
        ctx.require(Role.admin)
    m = _membership(ctx, user_id)
    if m.role == Role.owner:
        if ctx.role != Role.owner:
            raise HTTPException(403, "only owners can remove an owner")
        if _owner_count(ctx) == 1:
            raise HTTPException(409, "an organisation needs at least one owner")
    ctx.session.delete(m)
