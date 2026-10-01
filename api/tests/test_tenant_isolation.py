"""Organisation A must never see or change organisation B's data, through the API or
directly in the database (row-level security), even as the tables' owner."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.db import engine, set_context
from app.db import SessionLocal
from test_invitations import invite


def test_api_hides_other_organisations(alice, bob):
    acme = alice.create_org("Acme")
    bob.create_org("Globex")
    for path in ("", "/members", "/invitations"):
        assert bob.get(f"/api/orgs/{acme}{path}").status_code == 404, path
    assert bob.patch(f"/api/orgs/{acme}", json={"name": "pwned"}).status_code == 404
    assert bob.post(f"/api/orgs/{acme}/invitations", json={"email": "bob@globex.example"}).status_code == 404
    assert [o["name"] for o in bob.get("/api/me").json()["organisations"]] == ["Globex"]


def test_unknown_org_looks_the_same_as_someone_elses(bob):
    assert bob.get(f"/api/orgs/{uuid.uuid4()}").status_code == 404


def _ids(alice, bob):
    acme, globex = alice.create_org("Acme"), bob.create_org("Globex")
    return acme, globex, bob.get("/api/me").json()["id"]


def test_database_without_context_sees_nothing(alice, bob):
    _ids(alice, bob)
    with engine.connect() as conn:  # the app's own role, no tenant context set
        for table in ("users", "organisations", "memberships", "invitations"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0, table


def test_database_query_without_where_only_returns_own_org(alice, bob):
    acme, globex, bob_id = _ids(alice, bob)
    with SessionLocal() as s, s.begin():
        set_context(s, user_id=bob_id)
        assert s.execute(text("SELECT name FROM organisations")).scalars().all() == ["Globex"]
        set_context(s, org_id=globex)
        users = s.execute(text("SELECT email FROM users")).scalars().all()
        assert users == ["bob@globex.example"]


def test_database_refuses_writes_into_another_org(alice, bob):
    acme, globex, bob_id = _ids(alice, bob)
    with SessionLocal() as s, s.begin():
        set_context(s, user_id=bob_id, org_id=globex)
        with pytest.raises(ProgrammingError, match="row-level security"):
            s.execute(
                text("INSERT INTO memberships (org_id, user_id, role) VALUES (:o, :u, 'owner')"),
                {"o": acme, "u": bob_id},
            )
    with SessionLocal() as s, s.begin():
        set_context(s, user_id=bob_id, org_id=globex)
        # UPDATE/DELETE on another org's rows silently match nothing
        assert s.execute(text("UPDATE organisations SET name = 'pwned' WHERE id = :o"), {"o": acme}).rowcount == 0
        assert s.execute(text("DELETE FROM memberships WHERE org_id = :o"), {"o": acme}).rowcount == 0


def test_invitation_token_only_reveals_its_own_org(alice, bob, anon):
    acme = alice.create_org("Acme")
    bob.create_org("Globex")
    tok = invite(alice, acme, "carol@acme.example")
    assert anon.get(f"/api/invitations/{tok}").json()["organisation"] == "Acme"
    with SessionLocal() as s, s.begin():
        set_context(s, invite_hash="00" * 32)  # a wrong token sees nothing
        assert s.execute(text("SELECT count(*) FROM organisations")).scalar() == 0
