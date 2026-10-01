"""Background worker: runs jobs from the Postgres `jobs` table.

Several worker pods can run safely: each claims one job with SELECT ... FOR UPDATE SKIP LOCKED
inside a transaction, so a job is never handled twice. Failures back off exponentially and stop
after MAX_ATTEMPTS (the job keeps its last error for inspection).

  python -m app.worker
"""

import logging
import signal
import smtplib
import time
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .models import Job

MAX_ATTEMPTS = 8
log = logging.getLogger("eightguard.worker")
running = True


def send_email(payload: dict) -> None:
    msg = EmailMessage()
    msg["From"] = formataddr(parseaddr(settings.mail_from))
    msg["To"] = payload["to"]
    msg["Subject"] = payload["subject"]
    msg.set_content(payload["body"])
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(msg)


HANDLERS = {"email": send_email}


def run_one() -> bool:
    """Runs the next due job. Returns False when there was nothing to do."""
    with SessionLocal() as session, session.begin():
        job = session.scalar(
            select(Job)
            .where(Job.done_at.is_(None), Job.run_at <= datetime.now(UTC))
            .order_by(Job.run_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return False
        try:
            HANDLERS[job.kind](job.payload)
            job.done_at = datetime.now(UTC)
            log.info("job %s (%s) done", job.id, job.kind)
        except Exception as err:
            job.attempts += 1
            job.last_error = repr(err)[:2000]
            if job.attempts >= MAX_ATTEMPTS:
                job.done_at = datetime.now(UTC)
                log.error("job %s (%s) gave up after %d attempts: %r", job.id, job.kind, job.attempts, err)
            else:
                job.run_at = datetime.now(UTC) + timedelta(seconds=2**job.attempts)
                log.warning("job %s (%s) failed (attempt %d): %r", job.id, job.kind, job.attempts, err)
        return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    def stop(*_):
        global running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("worker started")
    while running:
        try:
            if not run_one():
                time.sleep(2)
        except Exception:
            log.exception("worker loop error")
            time.sleep(5)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
