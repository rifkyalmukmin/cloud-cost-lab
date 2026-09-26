# Production Readiness — Cloud Cost Lab

> Date: 2026-09-13 · Companion to [`docs/final-audit.md`](final-audit.md).
> Verdict: the project is **portfolio-complete** and follows production-grade practices, but ships deliberately as a **demo-scoped** deployment. This document states exactly what separates the two.

---

## 1. What is production-grade today

| Area | Evidence |
| --- | --- |
| Testing | 198 backend tests (pytest + real PostgreSQL test DB), 8 frontend tests, boundary/honesty coverage, CI-enforced |
| Static analysis | ruff + ESLint clean; **mypy strict: 0 issues**; tsc strict clean |
| CI/CD | GitHub Actions: lint/test/typecheck/build, Gitleaks, Trivy (HIGH/CRITICAL gate), multi-arch non-root Docker to GHCR; no auto-deploy |
| Security | no secrets in history (gitleaks full scan), least-privilege IAM design, dependency patching enforced via overrides, prompt-injection refusal |
| Observability | 7+ Prometheus metrics, SLIs/SLOs endpoint, alerts with runbook links, structured JSON logs with request-id correlation |
| Reliability | SLO targets defined (99.5% / 24h / 99%), 5 incident documents with exercised MTTD/MTTR, per-alert runbook |
| IaC | Terraform modules with secure defaults; fmt/validate green; plan reviewed (5 resources, 0 destroy); never applied |
| Data honesty | FRESH/STALE/UNKNOWN labelling; missing ≠ zero; UNALLOCATED ≠ guessed; negative realized savings stored as measured |

## 2. What keeps it out of production (deliberate)

| Gap | Why | Path to close |
| --- | --- | --- |
| Demo data by default | zero-credential safety posture (ADR-003) | enable billing export + monitoring (docs/gcp-setup.md §2) |
| No API authentication | single-user local demo | add authn/z before any shared deployment |
| Local state & single host | compose deployment on one machine | GCS backend + managed Postgres + multi-replica API |
| In-process SLIs | single-instance view | Prometheus scrape + `monitoring/prometheus-rules.yml` |
| No auto-deploy | §7 safety: apply is a human decision | WIF-based deploy workflow with plan approval (docs/gcp-setup.md) |

## 3. Go-live checklist (if ever deployed for real)

1. Billing export enabled and `_PARTITIONTIME` advancing daily.
2. `DEMO_MODE=false` with `GCP_BILLING_*` / `GCP_MONITORING_*` set; ADC/WIF verified.
3. `terraform apply` executed after a fresh, reviewed plan (cost: ~$0–1/month).
4. Authentication in front of the dashboard and API.
5. Prometheus scraping `/metrics` with `monitoring/prometheus-rules.yml` loaded and alert delivery wired.
6. GCS state backend configured for Terraform.
7. Budget alerts set (platform-side $50/70/90 plus cloud billing alerts).

## 4. Honest capability statement (for CV/interviews)

> "I built a GCP FinOps platform with production-grade engineering practices — tests, strict typing, security scanning, IaC, observability and incident runbooks — running on deterministic demo data. The GCP integrations are implemented and tested; enabling real data is a documented manual step I deliberately withheld because it creates billable resources."

This statement is verified by the repository contents as of this audit.
