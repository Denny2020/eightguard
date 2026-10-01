from conftest import ISSUER, token


def call(anon, tok):
    return anon.get("/api/me", headers={"Authorization": f"Bearer {tok}"})


def test_health(anon):
    assert anon.get("/healthz").json() == {"status": "ok"}
    assert anon.get("/readyz").json() == {"postgres": "ok"}


def test_requires_bearer_token(anon):
    assert anon.get("/api/me").status_code == 401
    assert anon.get("/api/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_rejects_wrong_audience_issuer_and_expired(anon):
    assert call(anon, token("s", "a@x.example", aud="someone-else")).status_code == 401
    assert call(anon, token("s", "a@x.example", iss=ISSUER + "-evil")).status_code == 401
    assert call(anon, token("s", "a@x.example", ttl=-120)).status_code == 401
    assert call(anon, "not.a.jwt").status_code == 401


def test_rejects_forged_signature(anon):
    from cryptography.hazmat.primitives.asymmetric import rsa
    import jwt, time

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())
    forged = jwt.encode(
        {"sub": "s", "email": "a@x.example", "email_verified": True, "iss": ISSUER, "aud": "eightguard-api", "iat": now, "exp": now + 60},
        other, algorithm="RS256",
    )
    assert call(anon, forged).status_code == 401


def test_requires_verified_email(anon):
    assert call(anon, token("s", "a@x.example", verified=False)).status_code == 403


def test_first_call_creates_the_user(alice):
    me = alice.get("/api/me").json()
    assert me["email"] == "alice@acme.example" and me["organisations"] == []
    assert alice.get("/api/me").json()["id"] == me["id"]  # same user on the next call
