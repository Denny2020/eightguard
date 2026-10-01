import { useEffect, useState } from "react";
import {
  api, E8_ANSWER_LABEL, ROLE_RANK,
  type E8Answer, type E8AnswerOut, type E8Assessment, type E8Content, type E8Plan, type E8PlanItem,
  type E8Requirement, type E8Snapshot, type E8Strategy, type Org,
} from "../api";
import { useApi, useTokenSource } from "../hooks";
import { Link } from "../router";
import { Card, ErrorBox, Spinner } from "../ui";

const LEVELS = [1, 2, 3];
const ANSWERS: E8Answer[] = ["yes", "partly", "no", "na"];
const EFFORT_LABEL = { low: "Quick win", medium: "Some work", high: "Project" };
const date = (iso: string) => new Date(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });

/** 0–3 as three segments. */
export function LevelMeter({ level, target }: { level: number; target?: number }) {
  return (
    <span className="meter" role="img" aria-label={`Maturity level ${level} of 3`}>
      {LEVELS.map((l) => (
        <span key={l} className={l <= level ? "on" : target !== undefined && l <= target ? "target" : ""} />
      ))}
    </span>
  );
}

function useE8(orgId: string) {
  const content = useApi<E8Content>("/e8/content", false);
  const assessment = useApi<E8Assessment>(`/orgs/${orgId}/e8`);
  return { content, assessment, error: content.error ?? assessment.error };
}

function Attribution({ content }: { content: E8Content }) {
  return (
    <p className="muted small attribution">
      {content.attribution} Source: <a href={content.source_url} target="_blank" rel="noreferrer">cyber.gov.au</a>,{" "}
      <a href={content.licence_url} target="_blank" rel="noreferrer">licence</a>. Self-assessment only; not an audit.
    </p>
  );
}

// ---------- Home: score, strategies, top of the plan, history ----------

export function E8Home({ org }: { org: Org }) {
  const token = useTokenSource();
  const { content, assessment, error } = useE8(org.id);
  const plan = useApi<E8Plan>(`/orgs/${org.id}/e8/plan`);
  const history = useApi<E8Snapshot[]>(`/orgs/${org.id}/e8/snapshots`);
  const [actionError, setActionError] = useState<Error | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const isAdmin = ROLE_RANK[org.role] >= ROLE_RANK.admin;

  if (error) return <ErrorBox error={error} />;
  if (!content.data || !assessment.data) return <Spinner />;
  const c = content.data;
  const a = assessment.data;
  const answered = new Set(a.answers.map((x) => x.key)).size;
  const totalKeys = new Set(c.requirements.map((r) => r.key)).size;

  async function run(action: () => Promise<unknown>, ok?: string) {
    setActionError(null);
    setNotice(null);
    try {
      await action();
      if (ok) setNotice(ok);
      assessment.reload();
      plan.reload();
      history.reload();
    } catch (err) {
      setActionError(err as Error);
    }
  }
  const setTarget = (target_level: number) =>
    run(() => api(`/orgs/${org.id}/e8`, token, { method: "PATCH", body: JSON.stringify({ target_level }) }));
  const complete = () =>
    confirm("Record today's result? It's saved permanently in your history.") &&
    run(() => api(`/orgs/${org.id}/e8/snapshots`, token, { method: "POST" }), "Assessment recorded.");

  const next = plan.data?.items.filter((i) => i.in_target) ?? [];
  return (
    <>
      <h1>Essential Eight</h1>
      <p className="muted">
        ASD's eight baseline strategies. Answer honestly: the score only counts a level when every requirement for it is
        in place.
      </p>
      {notice && <div className="alert success">{notice}</div>}
      {actionError && <ErrorBox error={actionError} />}

      <div className="grid">
        <Card title="Your maturity level">
          <div className="score">
            <span className="score-num">{a.score.overall_level}</span>
            <span className="muted">of 3 · your weakest strategy sets this</span>
          </div>
          <p className="muted small">
            {answered} of {totalKeys} questions answered
            {a.last_snapshot && <> · last recorded {date(a.last_snapshot.created_at)}</>}
          </p>
          {isAdmin && (
            <button className="btn primary small" onClick={complete} disabled={answered === 0}>
              Record result
            </button>
          )}
        </Card>
        <Card title="Target">
          <p className="muted small">Most small businesses aim for Level 1 first, then Level 2.</p>
          <div className="segmented" role="radiogroup" aria-label="Target maturity level">
            {LEVELS.map((l) => (
              <button
                key={l}
                role="radio"
                aria-checked={a.target_level === l}
                className={a.target_level === l ? "on" : ""}
                disabled={!isAdmin}
                onClick={() => setTarget(l)}
              >
                Level {l}
              </button>
            ))}
          </div>
          {!isAdmin && <p className="muted small">Admins set the target.</p>}
        </Card>
      </div>

      <Card title="Strategies">
        <ul className="strategies">
          {c.strategies.map((s) => {
            const sc = a.score.strategies.find((x) => x.code === s.code)!;
            return (
              <li key={s.code}>
                <Link href={`/o/${org.id}/e8/${s.code}`} className="strategy-link">
                  <span>
                    <strong>{s.name}</strong>
                    <span className="muted small">
                      {sc.next_level === null
                        ? "Level 3 reached"
                        : `${sc.next_met} of ${sc.next_total} in place for Level ${sc.next_level}`}
                    </span>
                  </span>
                  <LevelMeter level={sc.level} target={a.target_level} />
                </Link>
              </li>
            );
          })}
        </ul>
      </Card>

      <Card
        title={`Next steps for Level ${a.target_level}`}
        actions={<Link className="btn small ghost" href={`/o/${org.id}/e8/plan`}>Full plan</Link>}
      >
        {!plan.data ? (
          <Spinner />
        ) : next.length === 0 ? (
          <p className="muted">Everything for Level {a.target_level} is in place. Consider raising your target.</p>
        ) : (
          <PlanList orgId={org.id} items={next.slice(0, 8)} strategies={c.strategies} />
        )}
      </Card>

      {history.data && history.data.length > 0 && (
        <Card title="History">
          <table className="table">
            <thead>
              <tr>
                <th>Recorded</th>
                <th>Level</th>
                {c.strategies.map((s) => <th key={s.code} title={s.name}>{s.code}</th>)}
              </tr>
            </thead>
            <tbody>
              {history.data.map((h) => (
                <tr key={h.id}>
                  <td>
                    {date(h.created_at)}
                    <div className="muted small">{h.created_by ?? "former member"}</div>
                  </td>
                  <td><strong>{h.overall_level}</strong></td>
                  {c.strategies.map((s) => (
                    <td key={s.code}>{h.score.strategies.find((x) => x.code === s.code)?.level ?? "–"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <Attribution content={c} />
    </>
  );
}

// ---------- Action plan ----------

function PlanList({ orgId, items, strategies }: { orgId: string; items: E8PlanItem[]; strategies: E8Strategy[] }) {
  const name = (code: string) => strategies.find((s) => s.code === code)?.name ?? code;
  return (
    <ol className="plan">
      {items.map((i) => (
        <li key={i.key}>
          <div>
            <Link href={`/o/${orgId}/e8/${i.strategies[0]}#${i.key}`}><strong>{i.title}</strong></Link>
            <div className="muted small">
              Level {i.level} · {i.strategies.map(name).join(", ")}
              {i.answer && <> · answered “{E8_ANSWER_LABEL[i.answer]}”</>}
            </div>
          </div>
          <span className={`effort ${i.effort}`}>{EFFORT_LABEL[i.effort]}</span>
        </li>
      ))}
    </ol>
  );
}

export function E8PlanPage({ org }: { org: Org }) {
  const content = useApi<E8Content>("/e8/content", false);
  const plan = useApi<E8Plan>(`/orgs/${org.id}/e8/plan`);
  if (content.error || plan.error) return <ErrorBox error={(content.error ?? plan.error)!} />;
  if (!content.data || !plan.data) return <Spinner />;
  const { items, target_level } = plan.data;
  return (
    <>
      <p className="crumbs"><Link href={`/o/${org.id}/e8`}>Essential Eight</Link> ›</p>
      <h1>Action plan</h1>
      <p className="muted">
        Everything not yet in place, most important first: what you need for your Level {target_level} target, then
        what comes after.
      </p>
      {LEVELS.map((l) => {
        const group = items.filter((i) => i.level === l);
        if (group.length === 0) return null;
        return (
          <Card key={l} title={`Level ${l}${l > target_level ? " (beyond your target)" : ""} · ${group.length} to do`}>
            <PlanList orgId={org.id} items={group} strategies={content.data!.strategies} />
          </Card>
        );
      })}
      {items.length === 0 && <Card><p>Nothing left to do: every requirement is in place.</p></Card>}
      <Attribution content={content.data} />
    </>
  );
}

// ---------- One strategy's questions ----------

export function E8StrategyPage({ org, code }: { org: Org; code: string }) {
  const token = useTokenSource();
  const { content, assessment, error } = useE8(org.id);
  // local copy so answers show immediately; the server copy refreshes the score
  const [answers, setAnswers] = useState<Record<string, E8AnswerOut>>({});
  const [saveError, setSaveError] = useState<Error | null>(null);
  const canAnswer = ROLE_RANK[org.role] >= ROLE_RANK.member;

  useEffect(() => {
    if (assessment.data) setAnswers(Object.fromEntries(assessment.data.answers.map((x) => [x.key, x])));
  }, [assessment.data]);

  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id && content.data && assessment.data) document.getElementById(id)?.scrollIntoView({ block: "center" });
  }, [content.data, assessment.data]);

  if (error) return <ErrorBox error={error} />;
  if (!content.data || !assessment.data) return <Spinner />;
  const c = content.data;
  const strategy = c.strategies.find((s) => s.code === code);
  if (!strategy) return <ErrorBox error={new Error("Unknown strategy")} />;
  const index = c.strategies.indexOf(strategy);
  const prev = c.strategies[index - 1];
  const next = c.strategies[index + 1];
  const reqs = c.requirements.filter((r) => r.strategy === code);
  const score = assessment.data.score.strategies.find((s) => s.code === code)!;
  const target = assessment.data.target_level;

  async function save(key: string, answer: E8Answer | null, note: string) {
    setSaveError(null);
    const before = answers[key];
    try {
      if (answer === null) {
        setAnswers(({ [key]: _, ...rest }) => rest);
        await api(`/orgs/${org.id}/e8/answers/${key}`, token, { method: "DELETE" });
      } else {
        const optimistic = { key, answer, note, answered_by: null, answered_at: new Date().toISOString() };
        setAnswers((s) => ({ ...s, [key]: optimistic }));
        const saved = await api<E8AnswerOut>(`/orgs/${org.id}/e8/answers/${key}`, token, {
          method: "PUT",
          body: JSON.stringify({ answer, note }),
        });
        setAnswers((s) => ({ ...s, [key]: saved }));
      }
      assessment.reload();
    } catch (err) {
      setAnswers((s) => (before ? { ...s, [key]: before } : (({ [key]: _, ...rest }) => rest)(s)));
      setSaveError(err as Error);
    }
  }

  return (
    <>
      <p className="crumbs"><Link href={`/o/${org.id}/e8`}>Essential Eight</Link> › {index + 1} of {c.strategies.length}</p>
      <div className="strategy-head">
        <div>
          <h1>{strategy.name}</h1>
          <p className="muted">{strategy.summary}</p>
        </div>
        <div className="strategy-score">
          <LevelMeter level={score.level} target={target} />
          <span className="small">Level {score.level}</span>
        </div>
      </div>
      {saveError && <ErrorBox error={saveError} />}
      {!canAnswer && <div className="alert info">You have read-only access.</div>}

      {LEVELS.map((l) => {
        const group = reqs.filter((r) => r.level === l);
        const done = group.filter((r) => answers[r.key]).length;
        return (
          <details key={l} className="level" open={l <= target}>
            <summary>
              <h2>Level {l}</h2>
              <span className="muted small">{done} of {group.length} answered{l > target && " · beyond your target"}</span>
            </summary>
            {group.map((r) => (
              <Question
                key={r.id}
                req={r}
                current={answers[r.key]}
                sharedWith={c.requirements.filter((x) => x.key === r.key && x.strategy !== code).map((x) => c.strategies.find((s) => s.code === x.strategy)!.name)}
                disabled={!canAnswer}
                onSave={(answer, note) => save(r.key, answer, note)}
              />
            ))}
          </details>
        );
      })}

      <div className="pager">
        {prev ? <Link className="btn ghost" href={`/o/${org.id}/e8/${prev.code}`}>← {prev.name}</Link> : <span />}
        {next ? (
          <Link className="btn primary" href={`/o/${org.id}/e8/${next.code}`}>{next.name} →</Link>
        ) : (
          <Link className="btn primary" href={`/o/${org.id}/e8`}>See your results →</Link>
        )}
      </div>
      <Attribution content={c} />
    </>
  );
}

function Question({ req, current, sharedWith, disabled, onSave }: {
  req: E8Requirement;
  current: E8AnswerOut | undefined;
  sharedWith: string[];
  disabled: boolean;
  onSave: (answer: E8Answer | null, note: string) => void;
}) {
  const [note, setNote] = useState(current?.note ?? "");
  const [showNote, setShowNote] = useState(Boolean(current?.note));
  useEffect(() => setNote(current?.note ?? ""), [current?.note]);

  return (
    <div className="question" id={req.key}>
      <div className="question-text">
        <strong>{req.title}</strong>
        <p className="muted small">{req.text}</p>
        <div className="small muted">
          <span className={`effort ${req.effort}`}>{EFFORT_LABEL[req.effort]}</span>
          {req.until && <span> · replaced by a stricter requirement at Level {req.until + 1}</span>}
          {sharedWith.length > 0 && <span> · also counts for {sharedWith.join(", ")}</span>}
          {current?.answered_by && <span> · answered by {current.answered_by}, {date(current.answered_at)}</span>}
        </div>
      </div>
      <div className="question-answer">
        <div className="segmented" role="radiogroup" aria-label={req.title}>
          {ANSWERS.map((a) => (
            <button
              key={a}
              role="radio"
              aria-checked={current?.answer === a}
              className={current?.answer === a ? `on ${a}` : ""}
              disabled={disabled}
              onClick={() => onSave(current?.answer === a ? null : a, note)}
            >
              {E8_ANSWER_LABEL[a]}
            </button>
          ))}
        </div>
        {current && !disabled && !showNote && (
          <button className="link-btn small" onClick={() => setShowNote(true)}>Add a note</button>
        )}
        {current && showNote && (
          <textarea
            aria-label={`Note for ${req.title}`}
            maxLength={2000}
            rows={2}
            placeholder="How it's done, exceptions, who owns it…"
            value={note}
            disabled={disabled}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => note !== current.note && onSave(current.answer, note)}
          />
        )}
      </div>
    </div>
  );
}
