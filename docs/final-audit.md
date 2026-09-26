# Final Audit — Cloud Cost Lab

> Date: 2026-09-13 · Phase 14 (final hardening) · Auditors' lenses: architecture, code, security, GCP, Terraform, FinOps, cost, SRE, observability, testing, AI, documentation, portfolio.
> Scores at the bottom are a **project-specific self-assessment**, not an industry standard.

---

## 1. Validation battery (all green)

| Check | Result |
| --- | --- |
| Backend tests (pytest + PostgreSQL test DB) | **198 passed** |
| Backend lint (ruff check + format) | clean |
| Backend type check (mypy strict) | 0 issues in 59 files |
| Web lint (ESLint) | clean |
| Web type check (tsc --noEmit) | clean |
| Web tests (vitest) | 8 passed |
| Web production build (Next.js) | success |
| Workflow lint (actionlint × 3) | clean |
| Terraform fmt + validate (demo, dev) | success |
| Gitleaks (full history) | no leaks (after allowlist, see F-01) |
| Trivy fs (vuln/secret/misconfig, HIGH/CRITICAL gate) | 0 findings (after F-02) |
| `terraform apply` | **never run** |

## 2. Findings

### F-01 · HIGH — CI secret scan would fail on false positives
**Area:** security / CI. **Found:** Gitleaks flagged 8 "generic-api-key" findings — all the phrase *"Secret Manager,"* inside prose tables in `README.md` / `docs/project-roadmap.md`. Not real secrets, but `security.yml` (`gitleaks-action`, findings fail the run) would have gone red on main.
**Fixed:** `.gitleaks.toml` allowlist scoped precisely to those two markdown files and the `Secret Manager,?` prose pattern. Rescan: **no leaks** (18 commits, full history). Real secrets remain detected — the allowlist is file+regex scoped, not global.

### F-02 · HIGH — 2 HIGH CVEs in a transitive dependency
**Area:** security / dependencies. **Found:** Trivy flagged `postcss 8.4.31` (pulled by Next.js) — CVE-2026-45623 and CVE-2026-73646 (information disclosure / path traversal), fixed in 8.5.12/8.5.18. This would fail the security workflow's HIGH/CRITICAL gate.
**Fixed:** `overrides.postcss = "^8.5.18"` in `apps/web/package.json`; lockfile regenerated; all transitive installs now ≥ 8.5.18. Rescan: **0 HIGH/CRITICAL**. Web battery re-run green.

### F-03 · MEDIUM — Overview "Potential Savings" card was a stale placeholder
**Area:** portfolio / UX. **Found:** the Overview card still showed a "Phase 4" empty-state badge although the recommendation engine (Phase 5) has live data — a visible inconsistency during the demo.
**Fixed (Phase 15, verified here):** card wired to `GET /api/recommendations/savings` (presentation-layer only, existing endpoint, no core-logic change).

### F-04 · MEDIUM — demo script described a stale dataset state
**Area:** documentation. **Found:** the 5-minute script said "four findings" while the dataset produces five, and omitted the lifecycle-reset step.
**Fixed (Phase 15):** script corrected to the real five-finding state, includes `costlab.seed --force` reset, and turns the VERIFIED idle VM into a demo highlight.

### F-05 · LOW — duplicate editor/iCloud artifacts
**Area:** hygiene. **Found:** `site-header 2.tsx` (removed in Phase 11) and `.next`-internal duplicates (gitignored). **Status:** working tree verified clean; no tracked duplicates.

### F-06 · LOW — known, accepted limitations (documented, not fixed)
- Real-mode utilization has no samples until monitoring is enabled (honest "no data" surfaces).
- `GCPMonitoringProvider` maps `instance_id`/`database_id` labels as resource ids — a mapping table is needed at real scale.
- LLM advisor output is free-form text labelled "verify before use" (not parsed into the 7-section contract).
- Savings verification for scope-level findings (anomalies) requires a reported value.
- mypy strict: 0 issues; the historical baseline errors were eliminated in Phase 11.

## 3. Per-area notes

- **Architecture:** provider abstraction (billing/monitoring/AI) holds — demo and GCP implementations share contracts; no layer knows the mode. Route ordering issue (static before dynamic) caught and fixed in Phase 13.
- **Code:** strict typing green across 59 files; dead code and duplicate test files removed in earlier phases.
- **Security:** no secrets tracked (gitleaks full history clean); `.env`/keys git-ignored; CI uses ephemeral tokens; AI read-only with injection refusal; Docker non-root + pinned.
- **GCP:** zero billable resources created; providers dormant; least-privilege IAM documented.
- **Terraform:** fmt/validate green both environments; plan = 5 to add, 0 destroy; never applied.
- **FinOps/Cost:** potential-vs-realized separation enforced (409-refusal, negative stored); budgets + advisory policies; BQ cost guards test-asserted.
- **SRE/Observability:** 7+ metrics on `/metrics`, SLIs/SLOs, alerts with runbook links, JSON logs, 5 incident exercises with MTTD/MTTR.
- **Testing:** 198 backend + 8 frontend tests; coverage of boundary conditions, honesty guards, and lifecycle flows.
- **AI:** deterministic default advisor; LLM optional; injection-refusal tested.
- **Documentation/Portfolio:** 20+ docs, 13-section README, 5 portfolio documents, 8 live screenshots with refresh guide.

## 4. Scores (project-specific self-assessment — NOT an industry standard)

| Dimension | Score | Basis | Deductions |
| --- | --- | --- | --- |
| **Security** | **92 / 100** | scans clean, no secrets in history, least-privilege design, read-only AI, injection defence | no API authentication (demo scope); WIF documented but not exercised |
| **FinOps** | **90 / 100** | potential-vs-realized discipline, budgets, policies, cost-guarded BQ, IaC cost docs | unit economics and what-if simulator not built |
| **SRE** | **85 / 100** | metrics, SLIs/SLOs, alerting, runbooks, incident docs | SLIs are single-instance/in-process; no live Prometheus deployment |
| **Testing** | **85 / 100** | 206 tests, boundary + honesty coverage, strict typing, CI gates | no end-to-end browser tests; no coverage-percentage tracking |
| **Portfolio** | **90 / 100** | 13-section README, live screenshots, demo script, CV/LinkedIn/interview pack, honest limitations | screenshots need a refresh after demo-state changes |

**Overall: 88 / 100** — production-grade *practices* on a demo-*scoped* deployment.
