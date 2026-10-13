# Security — Cloud Cost Lab

> Status: living document. Describes what is **implemented in this repository**;
> items that are not implemented are marked as such.
> Related: [`cost-safety.md`](cost-safety.md), [`gcp-setup.md`](gcp-setup.md),
> [`terraform.md`](terraform.md), [`governance.md`](governance.md),
> [ADR-005 AI safety](decisions/ADR-005-ai-safety.md).

## 1. Controls at a glance

| Area | Control | Where |
| --- | --- | --- |
| Secrets | No credentials in code; configuration via environment variables; `.env`, key files, `*.tfvars`, `backend.hcl` and state files are git-ignored; `.env.example` is placeholder-only | `.gitignore`, `.env.example` |
| Secret scanning | Gitleaks on pull requests, pushes to `main` and weekly | `.github/workflows/security.yml` |
| Write access | Every state-changing endpoint requires an `X-API-Key` header matched against `API_KEYS` (`name:key`, keys ≥ 16 chars, constant-time comparison); empty `API_KEYS` rejects all writes (fail closed); the key's name is the audit-log actor. Read endpoints are open (demo data only) | `apps/api/src/costlab/api/auth.py` |
| Browser access | CORS allow-list from `CORS_ORIGINS`; only `GET`/`POST`; no cookies/credentials | `apps/api/src/costlab/main.py` |
| AI | Read-only advisor; it cannot approve, implement or delete anything | ADR-005, `docs/ai-advisor.md` |
| Human approval | Recommendation lifecycle `OPEN → APPROVED → IMPLEMENTED → VERIFIED` with an audit log; nothing is auto-applied | `docs/governance.md`, `docs/savings.md` |
| Container | Multi-stage build, pinned base image, non-root user (uid 10001), no secrets in the image, `.dockerignore` keeps `.env`/state/keys out of the build context | `apps/api/Dockerfile`, `.dockerignore` |
| Image gate | CI asserts the container uid is not 0 and Trivy fails the run on fixable HIGH/CRITICAL findings (see §2) | `.github/workflows/build.yml` |
| IaC | Least-privilege service account, bucket/dataset-scoped grants, public access prevention, `force_destroy`/`delete_contents_on_destroy` off, no SA keys, GCS remote state (private, versioned) | `terraform/`, `terraform/README.md` |
| GCP identity | ADC locally, Workload Identity Federation preferred for deployment; no key files; platform identity is read-only | `docs/gcp-setup.md` |

Not implemented / not claimed: Secret Manager integration in code (secrets come
from the environment), an authenticated read API, per-user authorization beyond
the named API keys. API rate limiting is being added separately; check
`apps/api/README.md` for its final status.

## 2. Trivy and `ignore-unfixed: true`

### What is configured

`ignore-unfixed: true` is set on the two **gating** Trivy steps:

| Workflow | Step | Scope | Gate |
| --- | --- | --- | --- |
| `build.yml` | Trivy image scan | the built API image (OS packages + Python packages) | `severity: CRITICAL,HIGH`, `exit-code: 1` |
| `security.yml` | Trivy filesystem scan | repo files (npm lockfile, IaC misconfig, secrets) | `severity: CRITICAL,HIGH`, `exit-code: 1` |

A third step in `security.yml` (informational filesystem report) scans for
`MEDIUM,LOW` vulnerabilities with `exit-code: 0` and **without**
`ignore-unfixed`.

### What it means

Trivy normally reports every known CVE in the image. With `ignore-unfixed`, it
drops findings for which the advisory database lists **no fixed version** yet
(typical for Debian base-image packages the vendor has not patched). The gate
therefore fails only on vulnerabilities that can be fixed today by upgrading a
package or the base image.

### Why it was chosen

- The base image (`python:3.13.1-slim-bookworm`) regularly carries HIGH OS-level
  CVEs with no upstream fix. Without the flag the gate would stay red for
  reasons nobody can act on, and a permanently red gate gets ignored.
- A gate should be actionable: every failure it reports has a concrete remedy
  (bump a dependency, rebuild/bump the base image).
- It keeps the project's "findings block merges" rule realistic for a
  single-maintainer student project.

### Risk it introduces

- **Unfixed HIGH/CRITICAL CVEs are hidden from the gate.** A serious unpatched
  vulnerability in the base image or a dependency will not fail CI and will not
  appear in any blocking output.
- **Fix-availability changes silently.** A finding is hidden today and becomes a
  failure the day a fix is published, possibly in a PR unrelated to it.
- **Reachability is not assessed either way**: hidden findings may or may not be
  exploitable in this application; the flag removes the information needed to
  decide.
- Today, **no workflow shows unfixed HIGH/CRITICAL findings at all**: the
  informational report only covers MEDIUM/LOW. This is the main gap in the
  compensating controls.

### Compensating controls

| Control | Status |
| --- | --- |
| Severity gate: fixable HIGH/CRITICAL fail the run | Implemented (both gates) |
| Gitleaks, non-root check, pinned base image tag, no `latest` tag published | Implemented |
| Weekly scheduled rescan of the repository (new CVEs against unchanged code) | Implemented for the **filesystem** scan only (`security.yml`, Mondays 06:00 UTC). The image scan runs only when `apps/api/**`, `data/mock/**` or `build.yml` change |
| Periodic review of the **unfiltered** report | **Not implemented yet** — see recommendations |
| Periodic base image rebuild / bump | Manual. Review the pinned tag at least monthly and whenever the scheduled scan or the image gate reports a fixable finding |
| Dependency overrides for transitive fixes (e.g. `postcss` in `apps/web/package.json`) | Used when needed (see `docs/final-audit.md` F-02) |

### Recommendations (not applied — workflow behaviour is unchanged)

1. **Add visibility, not a new blocker.** Change the informational report step in
   `security.yml` to cover all severities (`UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL`)
   without `ignore-unfixed`, keep `exit-code: 0`, and review it weekly. Add the
   same unfiltered, non-blocking scan for the built image.
2. **Schedule the image scan** (weekly `schedule:` trigger on `build.yml`, or a
   small separate workflow) so new CVEs in the unchanged base image are noticed.
3. **Gate order in `build.yml`:** on `main` the image is built *and pushed to
   GHCR* before the Trivy step runs, so a failing scan does not stop
   publication of that SHA-tagged image. Prefer scan-then-push (build, `load`,
   scan, then push the same image) if published images should be pre-vetted.
4. **Prefer targeted ignores over a blanket flag** where practical: a
   `.trivyignore` with one entry per CVE, a justification and an expiry date is
   reviewable; a global flag is not.
5. The pinned base (`python:3.13.1`) is old; bump to a current `3.13.x` slim tag
   (and re-run the image scan) as routine maintenance.

### When to remove `ignore-unfixed`

Replace the blanket flag (use targeted `.trivyignore` entries or an unfiltered
gate) when **any** of these becomes true:

- the project is deployed anywhere other than a local demo, or handles real
  billing data from a production GCP organisation;
- the image moves to a much smaller base (distroless/minimal) where unfixed
  noise is low enough to triage individually;
- the unfiltered weekly report is in place and the hidden set is small enough to
  review and justify entry by entry;
- an unfixed HIGH/CRITICAL finding is judged reachable in this application (add
  a dated `.trivyignore`/VEX decision for the rest instead of hiding all).

Revisit this section whenever the Trivy action, the base image or the
deployment model changes.
