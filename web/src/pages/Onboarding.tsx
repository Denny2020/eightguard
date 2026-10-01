import { useState, type FormEvent } from "react";
import { api, ROLE_LABEL, type MyInvitation, type Org, type OrgSummary } from "../api";
import { useApi, useTokenSource } from "../hooks";
import { navigate } from "../router";
import { Card, ErrorBox, Spinner } from "../ui";

/** First stop for a signed-in user with no organisation. Invitations addressed to their
 *  verified email come first: most people arrive because a colleague invited them. */
export function Onboarding({ onCreated }: { onCreated: () => void }) {
  const token = useTokenSource();
  const invitations = useApi<MyInvitation[]>("/me/invitations");
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function join(inv: MyInvitation) {
    setBusy(inv.id);
    setError(null);
    try {
      const org = await api<OrgSummary>(`/me/invitations/${inv.id}/accept`, token, { method: "POST" });
      onCreated();
      navigate(`/o/${org.id}`);
    } catch (err) {
      setError(err as Error);
      setBusy(null);
      invitations.reload();
    }
  }

  if (!invitations.data && !invitations.error) return <Spinner />;
  const pending = invitations.data ?? [];

  if (pending.length === 0) {
    return (
      <div className="narrow">
        <h1>Set up your organisation</h1>
        <p className="muted">
          You'll be its owner and can invite your team next. Joining a colleague's organisation instead? Ask them to
          invite this email address.
        </p>
        <CreateOrg onCreated={onCreated} />
      </div>
    );
  }

  return (
    <div className="narrow">
      <h1>You've been invited</h1>
      <p className="muted">Join your team's organisation to get started.</p>
      {error && <ErrorBox error={error} />}
      {pending.map((inv) => (
        <Card key={inv.id}>
          <div className="invite-row">
            <div>
              <h2>{inv.organisation}</h2>
              <p className="muted small">
                as {ROLE_LABEL[inv.role]} · expires {new Date(inv.expires_at).toLocaleDateString("en-AU")}
              </p>
            </div>
            <button className="btn primary" disabled={busy !== null} onClick={() => join(inv)}>
              {busy === inv.id ? "Joining…" : "Join"}
            </button>
          </div>
        </Card>
      ))}
      <details className="secondary">
        <summary>Or set up a separate organisation of your own</summary>
        <CreateOrg onCreated={onCreated} />
      </details>
    </div>
  );
}

function CreateOrg({ onCreated }: { onCreated: () => void }) {
  const token = useTokenSource();
  const [name, setName] = useState("");
  const [abn, setAbn] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const org = await api<Org>("/orgs", token, {
        method: "POST",
        body: JSON.stringify({ name, abn: abn.replace(/\s/g, "") || null }),
      });
      onCreated();
      navigate(`/o/${org.id}`);
    } catch (err) {
      setError(err as Error);
      setBusy(false);
    }
  }

  return (
    <Card>
      <form className="form" onSubmit={submit}>
        <label>
          Business name
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        </label>
        <label>
          ABN <span className="muted">(optional)</span>
          <input value={abn} onChange={(e) => setAbn(e.target.value)} inputMode="numeric" placeholder="11 digits" />
        </label>
        {error && <ErrorBox error={error} />}
        <button className="btn primary" disabled={busy}>Create organisation</button>
      </form>
    </Card>
  );
}
