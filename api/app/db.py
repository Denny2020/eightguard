"""Database access with per-request tenant context.

Every request runs in one transaction. Before any query, the request's identity is written to
transaction-local settings (app.user_sub, app.user_id, app.org_id). Postgres row-level security
policies read those settings, so a query only ever sees the caller's own rows, even if the
code forgets a WHERE clause. Tables use FORCE ROW LEVEL SECURITY, so this applies to the table
owner too (the app's database user), not just to other roles.
"""

from collections.abc import Iterator
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def normalize_url(url: str) -> str:
    """Use the psycopg 3 driver for plain postgres URLs (e.g. CloudNativePG's `uri` secret key)."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Base(DeclarativeBase):
    pass


engine = create_engine(normalize_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One transaction per request, committed at the end (rolled back on error)."""
    with SessionLocal() as session, session.begin():
        yield session


def set_context(session: Session, **values: str | UUID | None) -> None:
    """Sets app.<name> for the rest of this transaction only (set_config(..., is_local => true))."""
    for name, value in values.items():
        session.execute(
            text("SELECT set_config(:name, :value, true)"),
            {"name": f"app.{name}", "value": "" if value is None else str(value)},
        )
