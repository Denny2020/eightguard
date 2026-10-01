import type { E8Assessment, E8Content, Member, Org } from "../api";
import { useApi } from "../hooks";
import { Link } from "../router";
import { Card } from "../ui";
import { LevelMeter } from "./E8";

export function Overview({ org }: { org: Org }) {
  const { data: members } = useApi<Member[]>(`/orgs/${org.id}/members`);
  const { data: content } = useApi<E8Content>("/e8/content", false);
  const { data: e8 } = useApi<E8Assessment>(`/orgs/${org.id}/e8`);
  const started = Boolean(e8 && e8.answers.length > 0);
  return (
    <>
      <h1>{org.name}</h1>
      <p className="muted">Your cyber readiness at a glance.</p>
      <div className="grid">
        <Card
          title="Essential Eight"
          actions={<Link className="btn small ghost" href={`/o/${org.id}/e8`}>{started ? "Open" : "Start"}</Link>}
        >
          <div className="score">
            <span className="score-num">{e8 ? (started ? e8.score.overall_level : "–") : "…"}</span>
            <span className="muted">maturity level · target {e8?.target_level ?? "…"}</span>
          </div>
          {!started && <p className="muted small">Answer the guided questions to get your score and a step-by-step plan.</p>}
          {content && e8 && (
            <ul className="mini-strategies">
              {content.strategies.map((s) => (
                <li key={s.code}>
                  <span>{s.name}</span>
                  <LevelMeter level={e8.score.strategies.find((x) => x.code === s.code)?.level ?? 0} target={e8.target_level} />
                </li>
              ))}
            </ul>
          )}
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
