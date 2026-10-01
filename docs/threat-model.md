# EightGuard threat model

Version 1 (Phase 1: sign-in, organisations, invitations). Method: STRIDE per component, reviewed
whenever a feature adds a data flow. Requirement baseline: OWASP ASVS level 2.

## What we protect

| Asset | Why it matters |
|---|---|
| Each organisation's security posture (assessments, evidence, plans, breach register) | A map of a business's weaknesses: valuable to attackers, damaging if leaked |
| Accounts and sessions | Access to the above |
| Invitation links | Grant membership of an organisation |
| The software supply chain (code, images, deployment repo) | Compromise reaches every customer |

## Data flows and trust boundaries

```
Browser ──HTTPS──▶ Envoy Gateway ──▶ web (static, nginx)
   │                    └──────────▶ api (FastAPI) ──▶ Postgres (RLS)
   │                                   │                  ▲
   └──HTTPS (OIDC, PKCE)──▶ Keycloak    └── JWKS ─────────┘ worker ──SMTP──▶ mail
```

Boundaries: internet ↔ Gateway; Gateway ↔ cluster services; API ↔ database (the tenant
boundary is enforced *here*); CI ↔ registry/gitops; Argo CD ↔ cluster.

## STRIDE

| Threat | Example | Mitigation (now) | Later |
|---|---|---|---|
| **S**poofing | Stolen password; forged token | Keycloak with mandatory TOTP, brute-force lockout, 12+ char passwords; API verifies signature (realm JWKS), issuer, audience `eightguard-api`, expiry and a verified email | WebAuthn/passkeys; anomaly alerts in SIEM (Phase 3/7) |
| **T**ampering | Changing another org's data via API or SQL injection | RLS on every tenant table with `FORCE`; inserts/updates checked by `WITH CHECK`; ORM-parameterised queries; role checks (owner/admin/member/auditor) | Hash-chained audit log (Phase 4) |
| **R**epudiation | "I didn't change that role" | Request logs; invitations record who invited and who accepted | Tamper-evident audit trail (Phase 4), central logs in Elasticsearch (Phase 3) |
| **I**nformation disclosure | Org A reads org B; token leaks via Referer; enumeration of org ids | RLS (tested); 404 (not 403) for orgs you don't belong to; `Referrer-Policy: no-referrer`; `Cache-Control: no-store` on API; tokens in sessionStorage; strict CSP | Encryption of evidence files (Phase 4) |
| **D**enial of service | Invitation spam; login flooding | Keycloak brute-force protection; resource limits on pods | Rate limits at the Gateway, HPA (Phase 7/8), Cloudflare in front (Phase 8) |
| **E**levation of privilege | Admin makes themselves owner; forwarded invite link joins someone else; last owner removed | Only owners grant/revoke owner; invitations can't grant owner; invitation bound to the invited email; single-use, 7-day, hashed tokens; an org always keeps an owner | Kyverno + PSA restricted + NetworkPolicies (Phase 7) |

## Supply chain

| Risk | Control |
|---|---|
| Malicious or vulnerable dependency | Exact pins + lockfiles with hashes (pip `--require-hashes`, `npm ci`), npm install scripts disabled, `npm audit signatures`, dependency review on PRs, Dependabot |
| Compromised CI action | Actions pinned to commit SHAs; minimal `GITHUB_TOKEN` permissions |
| Tampered image | Trivy gate before push; cosign keyless signatures + SBOM attestations; deployed by digest; Kyverno verification (Phase 7) |
| Leaked secret | gitleaks in CI and pre-commit, GitHub push protection; no secrets in either repo |

## Known gaps (accepted for now)

1. **The app's database user owns its tables.** RLS is forced, but an injection that could run
   DDL could disable it. Phase 7 splits a migration owner role from a runtime role with only
   DML rights.
2. **No rate limiting on the API yet** (invitation sending, accept attempts).
3. **Lab-only trust:** the lab CA and `*.kubelab.local` certificates are for the home lab only.
4. **Keycloak admin console is reachable** on the lab hostname; in production it will be
   restricted to an admin network or disabled on the public hostname.
