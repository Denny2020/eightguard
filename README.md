# EightGuard

Cyber readiness for Australian small businesses.

Most small businesses know they should "do something about cyber security" but don't know where to
start, and can't prove what they've done to insurers, clients or the regulator. EightGuard walks a
business through a sensible baseline and keeps the evidence:

- **Essential Eight assessment**: plain-English questions, a maturity score and a prioritised action plan
- **Incident response plan builder**: who to call and what to do, as a versioned PDF
- **Policies and training**: generated policies, staff acknowledgements, training tracker
- **Privacy Act kit**: privacy policy generator and a data-breach register with the notification clock
- **Evidence and audit trail**: malware-scanned uploads and a tamper-evident change log

> Status: early development. Not affiliated with the Australian Signals Directorate (ASD) or the
> Australian Cyber Security Centre (ACSC).

## How it's built

FastAPI · React/TypeScript · Keycloak · PostgreSQL (CloudNativePG, row-level security) · Kubernetes ·
Argo CD (GitOps, Kustomize overlays) · ELK + OpenTelemetry · signed, scanned multi-arch images.
Developed in a home lab first, then deployed to Azure.

Related repos: `eightguard-gitops` (deployment, private) · [`eightguard-infra`](https://github.com/Denny2020/eightguard-infra) (Terraform)
