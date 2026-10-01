"""Tests run against a real Postgres (CI service container, or a scratch database).

EIGHTGUARD_TEST_ADMIN_URL must point at a superuser connection. The suite creates a
non-superuser role `eightguard_app` that owns a fresh `eightguard_test` database, runs the
migrations as that role and runs the app as that role, exactly like production (CloudNativePG's
app user). That matters: superusers bypass row-level security, so testing as one would hide leaks.

Tokens are minted with a throwaway RSA key; the API's JWKS lookup is replaced with that key.
"""

import os
import secrets
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ADMIN_URL = make_url(os.environ.get("EIGHTGUARD_TEST_ADMIN_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"))
APP_PASSWORD = secrets.token_urlsafe(16)
APP_URL = ADMIN_URL.set(username="eightguard_app", password=APP_PASSWORD, database="eightguard_test")
os.environ["EIGHTGUARD_DATABASE_URL"] = APP_URL.render_as_string(hide_password=False)
os.environ["EIGHTGUARD_PUBLIC_URL"] = "https://eightguard.test"

ISSUER = "https://auth.test/realms/eightguard"
os.environ["EIGHTGUARD_OIDC_ISSUER"] = ISSUER
os.environ["EIGHTGUARD_OIDC_AUDIENCE"] = "eightguard-api"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

auth.signing_key = lambda token: KEY.public_key()


@pytest.fixture(scope="session", autouse=True)
def database():
    admin = create_engine(ADMIN_URL.render_as_string(hide_password=False), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS eightguard_test WITH (FORCE)"))
        conn.execute(text("DROP ROLE IF EXISTS eightguard_app"))
        conn.execute(text(f"CREATE ROLE eightguard_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{APP_PASSWORD}'"))
        conn.execute(text("CREATE DATABASE eightguard_test OWNER eightguard_app"))
    command.upgrade(Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini")), "head")
    yield
    engine.dispose()
    admin.dispose()


@pytest.fixture(autouse=True)
def clean():
    # TRUNCATE isn't subject to row-level security, so this works without any tenant context
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE jobs, invitations, memberships, organisations, users CASCADE"))


def token(sub: str, email: str, *, verified=True, aud="eightguard-api", iss=ISSUER, ttl=300, name=None) -> str:
    now = int(time.time())
    claims = {
        "sub": sub, "email": email, "email_verified": verified, "name": name or email.split("@")[0].title(),
        "iss": iss, "aud": aud, "iat": now, "exp": now + ttl,
    }
    return jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "test"})


class User:
    """A signed-in test user with an API client."""

    def __init__(self, email: str):
        self.email = email
        self.sub = str(uuid.uuid4())
        self.client = TestClient(app)
        self.client.headers["Authorization"] = f"Bearer {token(self.sub, email)}"

    def __getattr__(self, method):  # alice.get(...), alice.post(...)
        return getattr(self.client, method)

    def create_org(self, name: str) -> str:
        r = self.post("/api/orgs", json={"name": name})
        assert r.status_code == 201, r.text
        return r.json()["id"]


@pytest.fixture
def alice():
    return User("alice@acme.example")


@pytest.fixture
def bob():
    return User("bob@globex.example")


@pytest.fixture
def carol():
    return User("carol@acme.example")


@pytest.fixture
def anon():
    return TestClient(app)
