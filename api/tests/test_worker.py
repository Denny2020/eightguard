from app import worker
from app.db import SessionLocal
from app.models import Job


def add_job(**payload):
    with SessionLocal() as s, s.begin():
        s.add(Job(kind="email", payload={"to": "x@acme.example", "subject": "hi", "body": "b", **payload}))


def test_worker_sends_and_marks_done(monkeypatch):
    sent = []
    monkeypatch.setitem(worker.HANDLERS, "email", sent.append)
    add_job()
    assert worker.run_one() is True
    assert worker.run_one() is False  # nothing left
    assert sent[0]["to"] == "x@acme.example"
    with SessionLocal() as s:
        assert s.query(Job).one().done_at is not None


def test_worker_backs_off_on_failure(monkeypatch):
    def boom(_):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setitem(worker.HANDLERS, "email", boom)
    add_job()
    assert worker.run_one() is True
    with SessionLocal() as s:
        job = s.query(Job).one()
        assert job.attempts == 1 and job.done_at is None and "smtp down" in job.last_error
    assert worker.run_one() is False  # retry is scheduled in the future
