"""Essential Eight assessment API."""

from test_orgs import _join


def base(org_id):
    return f"/api/orgs/{org_id}/e8"


def answer(user, org_id, key, value="yes", note=""):
    return user.put(f"{base(org_id)}/answers/{key}", json={"answer": value, "note": note})


def test_content_is_public_and_attributed(anon):
    body = anon.get("/api/e8/content").json()
    assert body["version"] == "e8mm-2023-11" and "CC BY 4.0" in body["attribution"]
    assert len(body["strategies"]) == 8 and len(body["requirements"]) == 152


def test_new_assessment_is_empty(alice):
    org = alice.create_org("Acme")
    body = alice.get(base(org)).json()
    assert body["target_level"] == 1 and body["answers"] == [] and body["last_snapshot"] is None
    assert body["score"]["overall_level"] == 0


def test_answers_update_the_score(alice):
    org = alice.create_org("Acme")
    content = alice.get("/api/e8/content").json()
    l1 = {r["key"] for r in content["requirements"] if r["level"] == 1}
    for key in l1:
        assert answer(alice, org, key).status_code == 200
    body = alice.get(base(org)).json()
    assert body["score"]["overall_level"] == 1 and len(body["answers"]) == len(l1)

    r = answer(alice, org, "BAK-1.04", "partly", note="  restore tested for files only  ")
    assert r.json()["note"] == "restore tested for files only" and r.json()["answered_by"] == "Alice"
    assert alice.get(base(org)).json()["score"]["overall_level"] == 0

    assert alice.delete(f"{base(org)}/answers/BAK-1.04").status_code == 204
    assert "BAK-1.04" not in {a["key"] for a in alice.get(base(org)).json()["answers"]}


def test_answer_validation(alice):
    org = alice.create_org("Acme")
    assert answer(alice, org, "NOPE-1.01").status_code == 404
    assert answer(alice, org, "MFA-1.01", "maybe").status_code == 422
    assert answer(alice, org, "MFA-1.01", note="x" * 2001).status_code == 422


def test_target_level_drives_the_plan(alice):
    org = alice.create_org("Acme")
    plan = alice.get(f"{base(org)}/plan").json()
    assert plan["target_level"] == 1 and plan["items"][0]["key"] == "MFA-1.01"
    assert alice.patch(base(org), json={"target_level": 3}).json()["target_level"] == 3
    assert alice.patch(base(org), json={"target_level": 4}).status_code == 422
    plan = alice.get(f"{base(org)}/plan").json()
    assert "PA-1.07" not in {i["key"] for i in plan["items"]}
    assert all(i["in_target"] for i in plan["items"])


def test_snapshots_freeze_the_result(alice):
    org = alice.create_org("Acme")
    assert alice.post(f"{base(org)}/snapshots").status_code == 409  # nothing answered yet
    answer(alice, org, "MFA-1.01", note="M365 security defaults on")
    snap = alice.post(f"{base(org)}/snapshots")
    assert snap.status_code == 201, snap.text
    snap = snap.json()
    assert snap["answers"] == {"MFA-1.01": {"answer": "yes", "note": "M365 security defaults on"}}
    assert snap["created_by"] == "Alice" and snap["content_version"] == "e8mm-2023-11"

    answer(alice, org, "MFA-1.01", "no")
    assert alice.get(f"{base(org)}/snapshots/{snap['id']}").json()["answers"]["MFA-1.01"]["answer"] == "yes"
    assert alice.get(base(org)).json()["last_snapshot"]["id"] == snap["id"]
    second = alice.post(f"{base(org)}/snapshots").json()
    assert [s["id"] for s in alice.get(f"{base(org)}/snapshots").json()] == [second["id"], snap["id"]]


def test_roles(alice, carol, bob):
    org = alice.create_org("Acme")
    _join(alice, carol, org, "member")
    _join(alice, bob, org, "auditor")
    answer(alice, org, "MFA-1.01")

    assert answer(carol, org, "MFA-1.02").status_code == 200
    assert carol.patch(base(org), json={"target_level": 2}).status_code == 403
    assert carol.post(f"{base(org)}/snapshots").status_code == 403

    assert bob.get(base(org)).status_code == 200 and bob.get(f"{base(org)}/plan").status_code == 200
    assert answer(bob, org, "MFA-1.03").status_code == 403
    assert bob.delete(f"{base(org)}/answers/MFA-1.01").status_code == 403
    assert {a["key"]: a["answered_by"] for a in bob.get(base(org)).json()["answers"]} == {
        "MFA-1.01": "Alice", "MFA-1.02": "Carol",
    }
