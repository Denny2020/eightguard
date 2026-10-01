import { useEffect } from "react";
import type { Me, Org } from "./api";
import { useAuth } from "./auth";
import { useApi } from "./hooks";
import { Invite } from "./pages/Invite";
import { Landing } from "./pages/Landing";
import { Onboarding } from "./pages/Onboarding";
import { Overview } from "./pages/Overview";
import { Team } from "./pages/Team";
import { Link, match, navigate, usePath } from "./router";
import { ErrorBox, Logo, Spinner } from "./ui";

export function App() {
  const auth = useAuth();
  const path = usePath();

  if (!auth.ready || path === "/callback") return <Spinner label="Signing you in" />;
  const invite = match("/invite/:token", path);
  if (invite) return <Invite token={invite.token} onJoined={() => {}} />;
  if (!auth.user) return <Landing />;
  return <SignedIn path={path} />;
}

function SignedIn({ path }: { path: string }) {
  const me = useApi<Me>("/me");
  const orgRoute = match("/o/:orgId", path) ?? match("/o/:orgId/:page", path);

  useEffect(() => {
    if (me.data && path === "/") {
      const first = me.data.organisations[0];
      navigate(first ? `/o/${first.id}` : "/onboarding", true);
    }
  }, [me.data, path]);

  if (me.error) return <div className="narrow"><ErrorBox error={me.error} /></div>;
  if (!me.data) return <Spinner />;
  if (path === "/onboarding" || me.data.organisations.length === 0) {
    return (
      <Frame me={me.data}>
        <Onboarding onCreated={me.reload} />
      </Frame>
    );
  }
  if (orgRoute) return <OrgArea me={me.data} orgId={orgRoute.orgId} page={orgRoute.page ?? "overview"} />;
  return <Spinner />;
}

function OrgArea({ me, orgId, page }: { me: Me; orgId: string; page: string }) {
  const org = useApi<Org>(`/orgs/${orgId}`);
  const nav = [
    ["overview", "Overview", `/o/${orgId}`],
    ["team", "Team", `/o/${orgId}/team`],
  ];
  return (
    <Frame me={me} orgId={orgId}>
      <div className="with-sidebar">
        <nav className="sidebar" aria-label="Organisation">
          {nav.map(([key, label, href]) => (
            <Link key={key} href={href} className={page === key ? "active" : ""} aria-current={page === key ? "page" : undefined}>
              {label}
            </Link>
          ))}
          <span className="soon">Essential Eight <em>soon</em></span>
          <span className="soon">Incident plan <em>soon</em></span>
          <span className="soon">Policies <em>soon</em></span>
        </nav>
        <main className="content">
          {org.error ? (
            <ErrorBox error={org.error} />
          ) : !org.data ? (
            <Spinner />
          ) : page === "team" ? (
            <Team org={org.data} myId={me.id} />
          ) : (
            <Overview org={org.data} />
          )}
        </main>
      </div>
    </Frame>
  );
}

function Frame({ me, orgId, children }: { me: Me; orgId?: string; children: React.ReactNode }) {
  const { signOut } = useAuth();
  return (
    <div className="app">
      <header className="topbar">
        <Link href="/" className="plain"><Logo /></Link>
        <div className="row">
          {me.organisations.length > 0 && (
            <select
              aria-label="Switch organisation"
              value={orgId ?? ""}
              onChange={(e) => navigate(e.target.value === "new" ? "/onboarding" : `/o/${e.target.value}`)}
            >
              {!orgId && <option value="">Choose organisation</option>}
              {me.organisations.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
              <option value="new">+ New organisation</option>
            </select>
          )}
          <span className="muted small hide-sm">{me.email}</span>
          <button className="btn small ghost" onClick={signOut}>Sign out</button>
        </div>
      </header>
      {children}
    </div>
  );
}
