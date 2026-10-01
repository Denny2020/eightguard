def test_create_org_makes_you_owner(alice):
    org_id = alice.create_org("Acme Plumbing")
    [org] = alice.get("/api/me").json()["organisations"]
    assert org == {"id": org_id, "name": "Acme Plumbing", "role": "owner"}
    assert alice.get(f"/api/orgs/{org_id}").json()["role"] == "owner"


def test_org_validation(alice):
    assert alice.post("/api/orgs", json={"name": ""}).status_code == 422
    assert alice.post("/api/orgs", json={"name": "X", "abn": "123"}).status_code == 422
    assert alice.post("/api/orgs", json={"name": "X", "abn": "51824753556"}).status_code == 201


def test_update_org_needs_admin(alice, carol):
    org_id = alice.create_org("Acme")
    _join(alice, carol, org_id, "member")
    assert carol.patch(f"/api/orgs/{org_id}", json={"name": "Hacked"}).status_code == 403
    assert alice.patch(f"/api/orgs/{org_id}", json={"name": "Acme Pty Ltd"}).json()["name"] == "Acme Pty Ltd"


def _join(owner, user, org_id, role):
    from app.db import SessionLocal
    from app.models import Job

    owner.post(f"/api/orgs/{org_id}/invitations", json={"email": user.email, "role": role})
    with SessionLocal() as s:
        link = [j for j in s.query(Job).all() if j.payload["to"] == user.email][-1].payload["body"]
    tok = link.split("/invite/")[1].split()[0]
    assert user.post(f"/api/invitations/{tok}/accept").status_code == 200
    return tok


def test_roles_and_last_owner(alice, carol):
    org_id = alice.create_org("Acme")
    _join(alice, carol, org_id, "admin")
    alice_id = alice.get("/api/me").json()["id"]
    carol_id = carol.get("/api/me").json()["id"]

    # admins can't touch the owner role
    assert carol.patch(f"/api/orgs/{org_id}/members/{alice_id}", json={"role": "member"}).status_code == 403
    assert carol.patch(f"/api/orgs/{org_id}/members/{carol_id}", json={"role": "owner"}).status_code == 403
    # the last owner can't step down or leave
    assert alice.patch(f"/api/orgs/{org_id}/members/{alice_id}", json={"role": "admin"}).status_code == 409
    assert alice.delete(f"/api/orgs/{org_id}/members/{alice_id}").status_code == 409
    # with a second owner, they can
    assert alice.patch(f"/api/orgs/{org_id}/members/{carol_id}", json={"role": "owner"}).status_code == 200
    assert alice.delete(f"/api/orgs/{org_id}/members/{alice_id}").status_code == 204
    assert alice.get(f"/api/orgs/{org_id}").status_code == 404


def test_members_list_and_auditor_is_read_only(alice, carol):
    org_id = alice.create_org("Acme")
    _join(alice, carol, org_id, "auditor")
    members = carol.get(f"/api/orgs/{org_id}/members").json()
    assert {(m["email"], m["role"]) for m in members} == {("alice@acme.example", "owner"), ("carol@acme.example", "auditor")}
    assert carol.post(f"/api/orgs/{org_id}/invitations", json={"email": "x@acme.example"}).status_code == 403
    assert carol.get(f"/api/orgs/{org_id}/invitations").status_code == 403
