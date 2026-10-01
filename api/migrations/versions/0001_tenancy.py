"""users, organisations, memberships, invitations, jobs, with row-level security

Revision ID: 0001
Revises:
Create Date: 2026-10-01

Tenant isolation lives in the database. The API writes the verified caller into
transaction-local settings (app.user_sub, app.user_id, app.org_id, app.invite_hash) and these
policies decide visibility. FORCE ROW LEVEL SECURITY makes them apply to the table owner too.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TYPE member_role AS ENUM ('owner', 'admin', 'member', 'auditor');

    CREATE TABLE users (
        id uuid PRIMARY KEY,
        sub varchar(255) NOT NULL UNIQUE,
        email varchar(320) NOT NULL,
        name varchar(200) NOT NULL DEFAULT '',
        created_at timestamptz NOT NULL DEFAULT now(),
        last_seen_at timestamptz
    );

    CREATE TABLE organisations (
        id uuid PRIMARY KEY,
        name varchar(120) NOT NULL CHECK (length(trim(name)) > 0),
        abn varchar(11) CHECK (abn ~ '^[0-9]{11}$'),
        created_by uuid NOT NULL REFERENCES users(id),
        created_at timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE memberships (
        org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role member_role NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (org_id, user_id)
    );
    CREATE INDEX ix_memberships_user_id ON memberships (user_id);

    CREATE TABLE invitations (
        id uuid PRIMARY KEY,
        org_id uuid NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
        email varchar(320) NOT NULL,
        role member_role NOT NULL CHECK (role <> 'owner'),
        token_hash bytea NOT NULL UNIQUE,
        invited_by uuid NOT NULL REFERENCES users(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        expires_at timestamptz NOT NULL,
        accepted_at timestamptz,
        accepted_by uuid REFERENCES users(id)
    );
    -- one open invitation per address per organisation
    CREATE UNIQUE INDEX ux_invitations_open ON invitations (org_id, lower(email)) WHERE accepted_at IS NULL;

    CREATE TABLE jobs (
        id bigserial PRIMARY KEY,
        kind varchar(60) NOT NULL,
        payload jsonb NOT NULL,
        run_at timestamptz NOT NULL DEFAULT now(),
        attempts integer NOT NULL DEFAULT 0,
        done_at timestamptz,
        last_error varchar(2000)
    );
    CREATE INDEX ix_jobs_pending ON jobs (run_at) WHERE done_at IS NULL;

    -- Caller context, read from transaction-local settings ('' when unset -> NULL)
    CREATE FUNCTION app_user_sub() RETURNS text LANGUAGE sql STABLE
        AS $$ SELECT NULLIF(current_setting('app.user_sub', true), '') $$;
    CREATE FUNCTION app_user_id() RETURNS uuid LANGUAGE sql STABLE
        AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;
    CREATE FUNCTION app_org_id() RETURNS uuid LANGUAGE sql STABLE
        AS $$ SELECT NULLIF(current_setting('app.org_id', true), '')::uuid $$;
    CREATE FUNCTION app_invite_hash() RETURNS bytea LANGUAGE sql STABLE
        AS $$ SELECT decode(NULLIF(current_setting('app.invite_hash', true), ''), 'hex') $$;

    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    ALTER TABLE users FORCE ROW LEVEL SECURITY;
    ALTER TABLE organisations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE organisations FORCE ROW LEVEL SECURITY;
    ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
    ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
    ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE invitations FORCE ROW LEVEL SECURITY;

    -- users: yourself (by Keycloak subject or id), plus teammates in the current organisation
    CREATE POLICY users_self ON users
        USING (sub = app_user_sub() OR id = app_user_id())
        WITH CHECK (sub = app_user_sub());
    CREATE POLICY users_teammates ON users FOR SELECT
        USING (id IN (SELECT user_id FROM memberships WHERE org_id = app_org_id()));

    -- memberships: your own (to list your organisations) and everyone in the current organisation
    CREATE POLICY memberships_read ON memberships FOR SELECT
        USING (user_id = app_user_id() OR org_id = app_org_id());
    CREATE POLICY memberships_insert ON memberships FOR INSERT
        WITH CHECK (org_id = app_org_id());
    CREATE POLICY memberships_update ON memberships FOR UPDATE
        USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
    CREATE POLICY memberships_delete ON memberships FOR DELETE
        USING (org_id = app_org_id());

    -- organisations: the current one, the ones you belong to, and the one you hold an invitation for
    CREATE POLICY organisations_read ON organisations FOR SELECT
        USING (
            id = app_org_id()
            OR id IN (SELECT org_id FROM memberships WHERE user_id = app_user_id())
            OR id IN (SELECT org_id FROM invitations WHERE token_hash = app_invite_hash())
        );
    CREATE POLICY organisations_insert ON organisations FOR INSERT
        WITH CHECK (created_by = app_user_id() AND id = app_org_id());
    CREATE POLICY organisations_update ON organisations FOR UPDATE
        USING (id = app_org_id()) WITH CHECK (id = app_org_id());
    CREATE POLICY organisations_delete ON organisations FOR DELETE
        USING (id = app_org_id());

    -- invitations: managed within the current organisation; readable by whoever holds the token
    CREATE POLICY invitations_org ON invitations
        USING (org_id = app_org_id()) WITH CHECK (org_id = app_org_id());
    CREATE POLICY invitations_token ON invitations FOR SELECT
        USING (token_hash = app_invite_hash());
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE jobs, invitations, memberships, organisations, users;
    DROP FUNCTION app_user_sub(), app_user_id(), app_org_id(), app_invite_hash();
    DROP TYPE member_role;
    """)
