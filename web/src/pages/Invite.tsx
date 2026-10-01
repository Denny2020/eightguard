import { useState } from "react";
import { api, ROLE_LABEL, type InvitationPreview, type OrgSummary } from "../api";
import { useAuth } from "../auth";
import { useApi } from "../hooks";
import { navigate } from "../router";
import { Card, ErrorBox, Logo, Spinner } from "../ui";

export function Invite({ token, onJoined }: { token: string; onJoined: () => void }) {
  const auth = useAuth();
  const preview = useApi<InvitationPreview>(`/invitations/${encodeURIComponent(token)}`, false);
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);

  async function accept() {
    setBusy(true);
    try {
      const org = await api<OrgSummary>(`/invitations/${encodeURIComponent(token)}/accept`, auth.accessToken, { method: "POST" });
      onJoined();
      navigate(`/o/${org.id}`);
    } catch (err) {
      setError(err as Error);
      setBusy(false);
    }
  }

  return (
    <div className="narrow">
      <p><Logo /></p>
      {preview.error ? (
        <Card title="Invitation unavailable">
          <p className="muted">This invitation has expired, was already used, or the link is wrong. Ask for a new one.</p>
        </Card>
      ) : !preview.data ? (
        <Spinner />
      ) : (
        <Card title={`Join ${preview.data.organisation}`}>
          <p>
            You've been invited as <strong>{ROLE_LABEL[preview.data.role]}</strong>. The invitation is for{" "}
            <strong>{preview.data.email}</strong>.
          </p>
          {error && <ErrorBox error={error} />}
          {auth.user ? (
            <div className="row">
              <button className="btn primary" disabled={busy} onClick={accept}>Accept invitation</button>
              <span className="muted small">Signed in as {auth.user.profile.email}</span>
            </div>
          ) : (
            <div className="row">
              <button className="btn primary" onClick={() => auth.signUp(`/invite/${token}`)}>Create account to accept</button>
              <button className="btn ghost" onClick={() => auth.signIn(`/invite/${token}`)}>I have an account</button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
