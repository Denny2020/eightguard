import { useAuth } from "../auth";
import { Logo } from "../ui";

const FEATURES = [
  ["Essential Eight, in plain English", "Answer guided questions and get a maturity score and a prioritised to-do list."],
  ["An incident response plan you'll actually use", "Who to call, what to do first, as a document your whole team can find."],
  ["Policies and staff training", "Generate the core policies, track acknowledgements and training."],
  ["Privacy Act ready", "A privacy policy and a data-breach register that tracks the notification clock."],
];

export function Landing() {
  const { signIn, signUp } = useAuth();
  return (
    <div className="landing">
      <header className="topbar">
        <Logo />
        <button className="btn ghost" onClick={() => signIn("/")}>Sign in</button>
      </header>
      <section className="hero">
        <p className="eyebrow">For Australian small businesses</p>
        <h1>Know where you stand on cyber security, and prove it.</h1>
        <p className="lead">
          EightGuard walks your business through the Essential Eight, builds your incident response plan and keeps the
          evidence your insurer, clients and regulator ask for.
        </p>
        <div className="row">
          <button className="btn primary big" onClick={() => signUp("/")}>Create a free account</button>
          <button className="btn ghost big" onClick={() => signIn("/")}>Sign in</button>
        </div>
        <p className="small muted">Multi-factor sign-in for every account. Your data stays in Australia.</p>
      </section>
      <section className="features">
        {FEATURES.map(([title, text]) => (
          <div key={title} className="feature">
            <h3>{title}</h3>
            <p className="muted">{text}</p>
          </div>
        ))}
      </section>
      <footer className="foot muted small">
        EightGuard is not affiliated with the Australian Signals Directorate or the Australian Cyber Security Centre.
      </footer>
    </div>
  );
}
