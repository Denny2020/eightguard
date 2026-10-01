import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, LargeBinary, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Role(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    auditor = "auditor"  # read-only, e.g. an insurer or external consultant


ROLE_RANK = {Role.auditor: 0, Role.member: 1, Role.admin: 2, Role.owner: 3}
role_type = Enum(Role, name="member_role", values_callable=lambda e: [r.value for r in e])


def new_id() -> uuid.UUID:
    return uuid.uuid7()  # time-ordered: friendlier to B-tree indexes than uuid4


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    sub: Mapped[str] = mapped_column(String(255), unique=True)  # Keycloak subject
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    abn: Mapped[str | None] = mapped_column(String(11))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    __tablename__ = "memberships"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[Role] = mapped_column(role_type)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))
    role: Mapped[Role] = mapped_column(role_type)
    # Only a SHA-256 of the token is stored; the token itself exists only in the email link.
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class E8Answer(str, enum.Enum):
    yes = "yes"
    partly = "partly"  # counts as not met
    no = "no"
    na = "na"  # not applicable: counts as met


e8_answer_type = Enum(E8Answer, name="e8_answer", values_callable=lambda e: [a.value for a in e])


class E8Assessment(Base):
    """The organisation's living Essential Eight assessment settings (one row per org)."""

    __tablename__ = "e8_assessments"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), primary_key=True)
    target_level: Mapped[int] = mapped_column(SmallInteger, default=1)
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class E8AnswerRow(Base):
    """The current answer to one requirement (by content answer key)."""

    __tablename__ = "e8_answers"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    answer: Mapped[E8Answer] = mapped_column(e8_answer_type)
    note: Mapped[str] = mapped_column(String(2000), default="")
    answered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class E8Snapshot(Base):
    """A completed assessment: score and answers frozen at that moment. Append-only (RLS has
    no UPDATE or DELETE policy)."""

    __tablename__ = "e8_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"))
    content_version: Mapped[str] = mapped_column(String(40))
    target_level: Mapped[int] = mapped_column(SmallInteger)
    overall_level: Mapped[int] = mapped_column(SmallInteger)
    score: Mapped[dict] = mapped_column(JSONB)
    answers: Mapped[dict] = mapped_column(JSONB)  # {key: {"answer": ..., "note": ...}}
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    """Background work, run by the worker (SELECT ... FOR UPDATE SKIP LOCKED)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSONB)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attempts: Mapped[int] = mapped_column(default=0)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(2000))
