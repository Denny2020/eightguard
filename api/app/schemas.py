import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import E8Answer, Role


class OrgSummary(BaseModel):
    id: uuid.UUID
    name: str
    role: Role


class Me(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    organisations: list[OrgSummary]


class OrgIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    abn: str | None = Field(default=None, pattern=r"^[0-9]{11}$")


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    abn: str | None
    created_at: datetime


class OrgDetail(OrgOut):
    role: Role  # the caller's role


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str
    role: Role
    joined_at: datetime


class RoleIn(BaseModel):
    role: Role


class InvitationIn(BaseModel):
    email: EmailStr
    role: Role = Role.member


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    created_at: datetime
    expires_at: datetime


class InvitationPreview(BaseModel):
    organisation: str
    email: str
    role: Role
    expires_at: datetime


class MyInvitation(BaseModel):
    id: uuid.UUID
    organisation: str
    role: Role
    expires_at: datetime


# Essential Eight

class E8StrategyOut(BaseModel):
    code: str
    name: str
    priority: int
    summary: str


class E8RequirementOut(BaseModel):
    id: str
    strategy: str
    level: int
    until: int | None
    key: str
    effort: str
    title: str
    text: str


class E8Content(BaseModel):
    version: str
    attribution: str
    source_url: str
    licence_url: str
    strategies: list[E8StrategyOut]
    requirements: list[E8RequirementOut]


class E8AnswerIn(BaseModel):
    answer: E8Answer
    note: str = Field(default="", max_length=2000)


class E8AnswerOut(BaseModel):
    key: str
    answer: E8Answer
    note: str
    answered_by: str | None  # name; None if they've since left the organisation
    answered_at: datetime


class E8StrategyScore(BaseModel):
    code: str
    level: int
    next_level: int | None
    next_met: int
    next_total: int


class E8Score(BaseModel):
    overall_level: int
    strategies: list[E8StrategyScore]


class E8SnapshotSummary(BaseModel):
    id: uuid.UUID
    content_version: str
    target_level: int
    overall_level: int
    score: E8Score
    created_by: str | None
    created_at: datetime


class E8SnapshotDetail(E8SnapshotSummary):
    answers: dict[str, dict]


class E8Assessment(BaseModel):
    content_version: str
    target_level: int
    answers: list[E8AnswerOut]
    score: E8Score
    last_snapshot: E8SnapshotSummary | None


class E8TargetIn(BaseModel):
    target_level: int = Field(ge=1, le=3)


class E8PlanItem(BaseModel):
    key: str
    level: int
    strategies: list[str]
    title: str
    text: str
    effort: str
    answer: E8Answer | None
    in_target: bool


class E8Plan(BaseModel):
    target_level: int
    items: list[E8PlanItem]
