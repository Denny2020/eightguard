import type { Member, Org } from "../api";
import { useApi } from "../hooks";
import { Link } from "../router";
import { Card } from "../ui";

const STRATEGIES = [
  "Patch applications", "Patch operating systems", "Multi-factor authentication", "Restrict admin privileges",
  "Application control", "Restrict Office macros", "User application hardening", "Regular backups",
];

export function Overview({ org }: { org: Org }) {
  const { data: members } = useApi<Member[]>(`/orgs/${org.id}/members`);
  return (
    <>
      <h1>{org.name}</h1>
      <p className="muted">Your cyber readiness at a glance.</p>
      <div className="grid">
        <Card title="Essential Eight">
          <div className="score">
            <span className="score-num">–</span>
            <span className="muted">maturity level</span>
          </div>
          <p className="muted small">The guided assessment arrives in the next release.</p>
          <ul className="checklist">
            {STRATEGIES.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </Card>
        <Card title="Team" actions={<Link className="btn small ghost" href={`/o/${org.id}/team`}>Manage</Link>}>
          <div className="score">
            <span className="score-num">{members ? members.length : "…"}</span>
            <span className="muted">{members?.length === 1 ? "person" : "people"}</span>
          </div>
          <p className="muted small">Invite the people who look after IT, finance and HR: they'll own parts of the plan.</p>
        </Card>
      </div>
    </>
  );
}
