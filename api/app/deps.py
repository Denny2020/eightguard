"""Request context: who is calling, and in which organisation.

`caller` upserts the user from the token and sets app.user_sub / app.user_id. `org_member`
checks the caller belongs to the organisation in the path, then sets app.org_id, after which
row-level security limits every query to that organisation.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .auth import Claims, current_claims
from .db import get_session, set_context
from .models import ROLE_RANK, Membership, Role, User, new_id


@dataclass
class Caller:
    session: Session
    user: User


@dataclass
class OrgCaller(Caller):
    org_id: uuid.UUID
    role: Role

    def require(self, minimum: Role) -> None:
        if ROLE_RANK[self.role] < ROLE_RANK[minimum]:
            raise HTTPException(403, f"requires the {minimum.value} role or higher")


def caller(claims: Claims = Depends(current_claims), session: Session = Depends(get_session)) -> Caller:
    # the email is verified (auth.verify rejects unverified addresses), so it can scope invitations
    set_context(session, user_sub=claims.sub, user_email=claims.email)
    user_id = session.scalar(
        insert(User)
        .values(id=new_id(), sub=claims.sub, email=claims.email, name=claims.name, last_seen_at=func.now())
        .on_conflict_do_update(
            index_elements=[User.sub],
            set_={"email": claims.email, "name": claims.name, "last_seen_at": func.now()},
        )
        .returning(User.id)
    )
    set_context(session, user_id=user_id)
    return Caller(session=session, user=session.get(User, user_id))


def org_member(org_id: uuid.UUID, me: Caller = Depends(caller)) -> OrgCaller:
    role = me.session.scalar(
        select(Membership.role).where(Membership.org_id == org_id, Membership.user_id == me.user.id)
    )
    if role is None:
        # 404, not 403: don't confirm that another organisation's id exists
        raise HTTPException(404, "organisation not found")
    set_context(me.session, org_id=org_id)
    return OrgCaller(session=me.session, user=me.user, org_id=org_id, role=role)
