import { useState, type FormEvent } from "react";
import { api, type Org } from "../api";
import { useTokenSource } from "../hooks";
import { navigate } from "../router";
import { Card, ErrorBox } from "../ui";

export function Onboarding({ onCreated }: { onCreated: () => void }) {
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
    <div className="narrow">
      <h1>Set up your organisation</h1>
      <p className="muted">You'll be its owner. You can invite your team next.</p>
      <Card>
        <form className="form" onSubmit={submit}>
          <label>
            Business name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} autoFocus />
          </label>
          <label>
            ABN <span className="muted">(optional)</span>
            <input value={abn} onChange={(e) => setAbn(e.target.value)} inputMode="numeric" placeholder="11 digits" />
          </label>
          {error && <ErrorBox error={error} />}
          <button className="btn primary" disabled={busy}>Create organisation</button>
        </form>
      </Card>
    </div>
  );
}
