"""let invitees see open invitations addressed to their verified email

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01

Fixes invitees landing on "set up your organisation" when the invitation link's browser state
is lost (e.g. Keycloak's verify-email link opens in a new tab). After sign-in the app now asks
for invitations addressed to the caller's verified email (app.user_email, from the token).
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE FUNCTION app_user_email() RETURNS text LANGUAGE sql STABLE
        AS $$ SELECT lower(NULLIF(current_setting('app.user_email', true), '')) $$;

    -- invitees: open, unexpired invitations addressed to their verified email
    CREATE POLICY invitations_invitee ON invitations FOR SELECT
        USING (lower(email) = app_user_email() AND accepted_at IS NULL AND expires_at > now());

    -- organisations: an org is visible if any invitation row you can see points to it. The
    -- subquery is itself filtered by the invitations policies (org, token holder, invitee).
    DROP POLICY organisations_read ON organisations;
    CREATE POLICY organisations_read ON organisations FOR SELECT
        USING (
            id = app_org_id()
            OR id IN (SELECT org_id FROM memberships WHERE user_id = app_user_id())
            OR id IN (SELECT org_id FROM invitations)
        );
    """)


def downgrade() -> None:
    op.execute("""
    DROP POLICY organisations_read ON organisations;
    CREATE POLICY organisations_read ON organisations FOR SELECT
        USING (
            id = app_org_id()
            OR id IN (SELECT org_id FROM memberships WHERE user_id = app_user_id())
            OR id IN (SELECT org_id FROM invitations WHERE token_hash = app_invite_hash())
        );
    DROP POLICY invitations_invitee ON invitations;
    DROP FUNCTION app_user_email();
    """)
