import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Role


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
