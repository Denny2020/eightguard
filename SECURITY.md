# Security policy

EightGuard handles sensitive information about small businesses' security posture, so we take
reports seriously.

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting:
**Security → Report a vulnerability** on this repository. Include what you found, how to
reproduce it, and the affected version or commit. You should get a reply within a week.

## How EightGuard is protected

- Sign-in through Keycloak (OIDC, PKCE) with mandatory multi-factor authentication
- Tenant isolation enforced by PostgreSQL row-level security, tested on every change
- Strict Content-Security-Policy, no third-party scripts, minimal frontend dependencies
- CodeQL, dependency review, gitleaks, secret scanning with push protection, npm signature checks
- Every image scanned with Trivy (fixable HIGH/CRITICAL blocks release), signed with cosign
  (keyless) and shipped with an SPDX SBOM; deployed by digest through GitOps

See [docs/threat-model.md](docs/threat-model.md).
