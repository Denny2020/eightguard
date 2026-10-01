import type { ReactNode } from "react";

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="center muted" role="status">
      <span className="spinner" aria-hidden="true" /> {label}…
    </div>
  );
}

export function ErrorBox({ error }: { error: Error }) {
  return (
    <div className="alert error" role="alert">
      {error.message}
    </div>
  );
}

export function Card({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Logo() {
  return (
    <span className="logo">
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 2 4 6.5v8.2C4 22.3 9.1 28.6 16 30c6.9-1.4 12-7.7 12-15.3V6.5z" />
        <text x="16" y="21" textAnchor="middle">8</text>
      </svg>
      EightGuard
    </span>
  );
}
