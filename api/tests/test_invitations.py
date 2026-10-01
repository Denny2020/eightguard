from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.db import SessionLocal, engine
from app.models import Job
from test_orgs import _join


def last_email():
    with SessionLocal() as s:
        return s.query(Job).order_by(Job.id.desc()).first().payload


def invite(owner, org_id, email, role="member"):
    r = owner.post(f"/api/orgs/{org_id}/invitations", json={"email": email, "role": role})
    assert r.status_code == 201, r.text
    body = last_email()["body"]
    return body.split("/invite/")[1].split()[0]


def test_invite_email_preview_and_accept(alice, carol, anon):
    org_id = alice.create_org("Acme")
    tok = invite(alice, org_id, "Carol@Acme.example")
    mail = last_email()
    assert mail["to"] == "carol@acme.example" and "https://eightguard.test/invite/" in mail["body"]

    preview = anon.get(f"/api/invitations/{tok}").json()
    assert preview["organisation"] == "Acme" and preview["role"] == "member"

    assert carol.post(f"/api/invitations/{tok}/accept").json()["role"] == "member"
    assert anon.get(f"/api/invitations/{tok}").status_code == 404  # single use
    assert [o["name"] for o in carol.get("/api/me").json()["organisations"]] == ["Acme"]


def test_invitation_is_bound_to_the_invited_email(alice, bob):
    org_id = alice.create_org("Acme")
    tok = invite(alice, org_id, "carol@acme.example")
    assert bob.post(f"/api/invitations/{tok}/accept").status_code == 403
    assert bob.get("/api/me").json()["organisations"] == []


def test_expired_and_unknown_tokens(alice, carol, anon):
    org_id = alice.create_org("Acme")
    tok = invite(alice, org_id, "carol@acme.example")
    with engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.org_id', :o, true)"), {"o": org_id})
        conn.execute(text("UPDATE invitations SET expires_at = :t"), {"t": datetime.now(UTC) - timedelta(minutes=1)})
    assert carol.post(f"/api/invitations/{tok}/accept").status_code == 404
    assert anon.get("/api/invitations/not-a-real-token").status_code == 404


def test_cannot_invite_owner_or_existing_member(alice, carol):
    org_id = alice.create_org("Acme")
    assert alice.post(f"/api/orgs/{org_id}/invitations", json={"email": "x@acme.example", "role": "owner"}).status_code == 422
    _join(alice, carol, org_id, "member")
    assert alice.post(f"/api/orgs/{org_id}/invitations", json={"email": "carol@acme.example"}).status_code == 409


def test_reinvite_replaces_and_revoke(alice):
    org_id = alice.create_org("Acme")
    invite(alice, org_id, "dave@acme.example")
    invite(alice, org_id, "dave@acme.example")
    [inv] = alice.get(f"/api/orgs/{org_id}/invitations").json()
    assert alice.delete(f"/api/orgs/{org_id}/invitations/{inv['id']}").status_code == 204
    assert alice.get(f"/api/orgs/{org_id}/invitations").json() == []
