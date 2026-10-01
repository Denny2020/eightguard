"""Background jobs live in Postgres (`jobs` table) and are written in the same transaction as
the change that caused them, so an invitation and its email are committed together."""

from sqlalchemy.orm import Session

from .models import Job


def enqueue(session: Session, kind: str, **payload) -> None:
    session.add(Job(kind=kind, payload=payload))


def send_email(session: Session, to: str, subject: str, body: str) -> None:
    enqueue(session, "email", to=to, subject=subject, body=body)
