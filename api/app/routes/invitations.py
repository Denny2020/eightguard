import hashlib
import uuid
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import jobs
from ..config import settings
from ..db import get_session, set_context
from ..deps import Caller, OrgCaller, caller, org_member
from ..models import Invitation, Membership, Organisation, Role, User
from ..schemas import InvitationIn, InvitationOut, InvitationPreview, MyInvitation, OrgSummary

router = APIRouter(prefix="/api")


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


@router.get("/orgs/{org_id}/invitations", response_model=list[InvitationOut])
def list_invitations(ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.admin)
    return ctx.session.scalars(
        select(Invitation)
        .where(Invitation.accepted_at.is_(None), Invitation.expires_at > func.now())
        .order_by(Invitation.created_at)
    ).all()


@router.post("/orgs/{org_id}/invitations", response_model=InvitationOut, status_code=201)
def invite(body: InvitationIn, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.admin)
    if body.role == Role.owner:
        raise HTTPException(422, "invite as admin, then promote to owner")
    email = body.email.lower()
    already = ctx.session.scalar(
        select(func.count()).select_from(Membership).join(User, User.id == Membership.user_id)
        .where(func.lower(User.email) == email)
    )
    if already:
        raise HTTPException(409, "already a member")
    # replace any open invitation for this address
    ctx.session.execute(
        delete(Invitation).where(func.lower(Invitation.email) == email, Invitation.accepted_at.is_(None))
    )
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        org_id=ctx.org_id,
        email=email,
        role=body.role,
        token_hash=_hash(token),
        invited_by=ctx.user.id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.invitation_ttl_days),
    )
    ctx.session.add(invitation)
    org = ctx.session.get(Organisation, ctx.org_id)
    jobs.send_email(
        ctx.session,
        to=email,
        subject=f"You're invited to {org.name} on EightGuard",
        body=(
            f"{ctx.user.name or ctx.user.email} has invited you to join {org.name} on EightGuard "
            f"as {body.role.value}.\n\nAccept the invitation (link valid for "
            f"{settings.invitation_ttl_days} days):\n{settings.public_url}/invite/{token}\n\n"
            "If you weren't expecting this, you can ignore this email.\n"
        ),
    )
    ctx.session.flush()
    return invitation


@router.delete("/orgs/{org_id}/invitations/{invitation_id}", status_code=204)
def revoke(invitation_id: uuid.UUID, ctx: OrgCaller = Depends(org_member)):
    ctx.require(Role.admin)
    ctx.session.execute(delete(Invitation).where(Invitation.id == invitation_id, Invitation.accepted_at.is_(None)))


def _open_invitation(session: Session, token: str) -> Invitation:
    set_context(session, invite_hash=_hash(token).hex())
    invitation = session.scalar(select(Invitation).where(Invitation.token_hash == _hash(token)))
    if invitation is None or invitation.accepted_at or invitation.expires_at <= datetime.now(UTC):
        raise HTTPException(404, "invitation not found or expired")
    return invitation


@router.get("/invitations/{token}", response_model=InvitationPreview)
def preview(token: str, session: Session = Depends(get_session)):
    """No sign-in needed: shows the invitee what they're accepting."""
    invitation = _open_invitation(session, token)
    org = session.get(Organisation, invitation.org_id)
    return InvitationPreview(
        organisation=org.name, email=invitation.email, role=invitation.role, expires_at=invitation.expires_at
    )


@router.post("/invitations/{token}/accept", response_model=OrgSummary)
def accept(token: str, me: Caller = Depends(caller)):
    invitation = _open_invitation(me.session, token)
    if invitation.email.lower() != me.user.email.lower():
        # a forwarded link must not let someone else join
        raise HTTPException(403, "this invitation is for a different email address")
    return _join(me, invitation)


@router.get("/me/invitations", response_model=list[MyInvitation])
def my_invitations(me: Caller = Depends(caller)):
    """Open invitations addressed to the caller's verified email (no link needed)."""
    rows = me.session.execute(
        select(Invitation.id, Organisation.name, Invitation.role, Invitation.expires_at)
        .join(Organisation, Organisation.id == Invitation.org_id)
        .where(func.lower(Invitation.email) == me.user.email.lower())
        .order_by(Invitation.created_at)
    ).all()
    return [MyInvitation(id=i, organisation=o, role=r, expires_at=e) for i, o, r, e in rows]


@router.post("/me/invitations/{invitation_id}/accept", response_model=OrgSummary)
def accept_mine(invitation_id: uuid.UUID, me: Caller = Depends(caller)):
    # row-level security only shows open invitations addressed to the caller's verified email
    invitation = me.session.scalar(select(Invitation).where(Invitation.id == invitation_id))
    if invitation is None or invitation.email.lower() != me.user.email.lower():  # defence in depth
        raise HTTPException(404, "invitation not found or expired")
    return _join(me, invitation)


def _join(me: Caller, invitation: Invitation) -> OrgSummary:
    set_context(me.session, org_id=invitation.org_id)
    if me.session.get(Membership, (invitation.org_id, me.user.id)) is None:
        me.session.add(Membership(org_id=invitation.org_id, user_id=me.user.id, role=invitation.role))
    invitation.accepted_at = datetime.now(UTC)
    invitation.accepted_by = me.user.id
    me.session.flush()
    org = me.session.get(Organisation, invitation.org_id)
    return OrgSummary(id=org.id, name=org.name, role=invitation.role)
