# .github/workflows/

GitHub Actions CI/CD for Cloud Cost Lab.

**Status: no workflow files yet.** CI/CD is introduced in **Phase 13** — adding pipelines before there is code to lint/test would only produce noise.

## Planned pipeline (once code exists)

1. lint
2. test (pytest for backend/analytics, unit tests for frontend)
3. build
4. security scan (Gitleaks secret scanning, Trivy filesystem scan)
5. Docker build
6. image scan (Trivy)
7. publish image (Artifact Registry) — only when configured
8. optional deployment — only when explicitly justified and cost-reviewed

## Ground rules

- Secrets are provided via GitHub Secrets — never committed files.
- GCP authentication from CI should use Workload Identity Federation when feasible; no static service account keys.
- Pipelines must stay cheap and fast; this is a student project on free-tier friendly limits.
