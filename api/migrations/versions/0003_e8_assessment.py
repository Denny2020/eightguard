"""Essential Eight assessment: settings, current answers, completed snapshots

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01

One living assessment per organisation. Answers are keyed by the content's answer key (see
app/e8/content.py). Completing an assessment freezes score and answers into an append-only
snapshot: there is no UPDATE or DELETE policy, so the app can't rewrite history.
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TYPE e8_answer AS ENUM ('yes', 'partly', 'no', 'na');

    CREATE TABLE e8_assessments (
        org_id uuid PRIMARY KEY REFERENCES organisations(id) ON DELETE CASCADE,
        target_level smallint NOT NULL DEFAULT 1 CHECK (target_level BETWEEN 1 AND 3),
        updated_by uuid NOT NULL REFERENCES users(id),
        updated_at timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE e8_answers (
        org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
        key varchar(32) NOT NULL,
        answer e8_answer NOT NULL,
        note varchar(2000) NOT NULL DEFAULT '',
        answered_by uuid NOT NULL REFERENCES users(id),
        answered_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (org_id, key)
    );

    CREATE TABLE e8_snapshots (
        id uuid PRIMARY KEY,
        org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
        content_version varchar(40) NOT NULL,
        target_level smallint NOT NULL CHECK (target_level BETWEEN 1 AND 3),
        overall_level smallint NOT NULL CHECK (overall_level BETWEEN 0 AND 3),
        score jsonb NOT NULL,
        answers jsonb NOT NULL,
        created_by uuid NOT NULL REFERENCES users(id),
        created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_e8_snapshots_org ON e8_snapshots (org_id, created_at DESC);

    ALTER TABLE e8_assessments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE e8_assessments FORCE ROW LEVEL SECURITY;
    ALTER TABLE e8_answers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE e8_answers FORCE ROW LEVEL SECURITY;
    ALTER TABLE e8_snapshots ENABLE ROW LEVEL SECURITY;
    ALTER TABLE e8_snapshots FORCE ROW LEVEL SECURITY;

    CREATE POLICY e8_assessments_org ON e8_assessments
        USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
    CREATE POLICY e8_answers_org ON e8_answers
        USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
    -- snapshots: read and append only
    CREATE POLICY e8_snapshots_read ON e8_snapshots FOR SELECT
        USING (org_id = app_org_id());
    CREATE POLICY e8_snapshots_insert ON e8_snapshots FOR INSERT
        WITH CHECK (org_id = app_org_id() AND created_by = app_user_id());
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE e8_snapshots, e8_answers, e8_assessments;
    DROP TYPE e8_answer;
    """)
