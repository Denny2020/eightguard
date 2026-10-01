import { useState, type FormEvent } from "react";
import { api, ROLE_LABEL, ROLE_RANK, type Invitation, type Member, type Org, type Role } from "../api";
import { useApi, useTokenSource } from "../hooks";
import { Card, ErrorBox, Spinner } from "../ui";

const date = (iso: string) => new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });

export function Team({ org, myId }: { org: Org; myId: string }) {
  const token = useTokenSource();
  const members = useApi<Member[]>(`/orgs/${org.id}/members`);
  const isAdmin = ROLE_RANK[org.role] >= ROLE_RANK.admin;
  const invites = useApi<Invitation[]>(isAdmin ? `/orgs/${org.id}/invitations` : null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  async function run(action: () => Promise<unknown>, ok?: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      if (ok) setNotice(ok);
      members.reload();
      invites.reload();
    } catch (err) {
      setError(err as Error);
    }
  }

  const invite = (e: FormEvent) => {
    e.preventDefault();
    run(
      () => api(`/orgs/${org.id}/invitations`, token, { method: "POST", body: JSON.stringify({ email, role }) }),
      `Invitation sent to ${email}`,
    ).then(() => setEmail(""));
  };
  const assignable: Role[] = org.role === "owner" ? ["owner", "admin", "member", "auditor"] : ["admin", "member", "auditor"];

  return (
    <>
      <h1>Team</h1>
      <p className="muted">Everyone here can see {org.name}'s readiness. Admins manage the team.</p>
      {notice && <div className="alert success">{notice}</div>}
      {error && <ErrorBox error={error} />}

      <Card title="Members">
        {!members.data ? (
          <Spinner />
        ) : (
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Role</th><th>Joined</th><th aria-label="Actions" /></tr>
            </thead>
            <tbody>
              {members.data.map((m) => {
                const canEdit = isAdmin && (org.role === "owner" || m.role !== "owner");
                return (
                  <tr key={m.user_id}>
                    <td>
                      <strong>{m.name || m.email}</strong>
                      {m.user_id === myId && <span className="tag">you</span>}
                      <div className="muted small">{m.email}</div>
                    </td>
                    <td>
                      {canEdit ? (
                        <select
                          value={m.role}
                          aria-label={`Role for ${m.email}`}
                          onChange={(e) =>
                            run(() =>
                              api(`/orgs/${org.id}/members/${m.user_id}`, token, {
                                method: "PATCH",
                                body: JSON.stringify({ role: e.target.value }),
                              }),
                            )
                          }
                        >
                          {(assignable.includes(m.role) ? assignable : [m.role, ...assignable]).map((r) => (
                            <option key={r} value={r}>{ROLE_LABEL[r]}</option>
                          ))}
                        </select>
                      ) : (
                        ROLE_LABEL[m.role]
                      )}
                    </td>
                    <td className="muted">{date(m.joined_at)}</td>
                    <td className="right">
                      {(canEdit || m.user_id === myId) && (
                        <button
                          className="btn small ghost danger"
                          onClick={() =>
                            confirm(m.user_id === myId ? `Leave ${org.name}?` : `Remove ${m.email}?`) &&
                            run(() => api(`/orgs/${org.id}/members/${m.user_id}`, token, { method: "DELETE" }))
                          }
                        >
                          {m.user_id === myId ? "Leave" : "Remove"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {isAdmin && (
        <Card title="Invite someone">
          <form className="form inline" onSubmit={invite}>
            <input type="email" required placeholder="name@business.com.au" value={email} onChange={(e) => setEmail(e.target.value)} aria-label="Email" />
            <select value={role} onChange={(e) => setRole(e.target.value as Role)} aria-label="Role">
              {(["admin", "member", "auditor"] as Role[]).map((r) => (
                <option key={r} value={r}>{ROLE_LABEL[r]}</option>
              ))}
            </select>
            <button className="btn primary">Send invitation</button>
          </form>
          {invites.data && invites.data.length > 0 && (
            <>
              <h3 className="sub">Pending</h3>
              <ul className="list">
                {invites.data.map((i) => (
                  <li key={i.id}>
                    <span>
                      <strong>{i.email}</strong> · {ROLE_LABEL[i.role]}
                      <span className="muted small"> · expires {date(i.expires_at)}</span>
                    </span>
                    <button className="btn small ghost" onClick={() => run(() => api(`/orgs/${org.id}/invitations/${i.id}`, token, { method: "DELETE" }))}>
                      Revoke
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}
    </>
  );
}
