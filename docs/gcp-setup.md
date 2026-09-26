# GCP Setup — Cloud Cost Lab (Phase 8)

> Status: Documented · Date: 2026-09-13
> Prerequisites for real billing data (`DEMO_MODE=false`). **Nothing in this document has been executed** — the platform currently runs in demo mode (CLAUDE.md §7: never silently create billable infrastructure).

---

## 1. Current GCP state (inspected 2026-09-13, read-only)

| Item | Value |
| --- | --- |
| gcloud SDK | 583.0.0 installed (`/opt/homebrew/bin/gcloud`) |
| Authenticated account | `ralkt25@gmail.com` (user account, `*` active) |
| Active project | `learn-cloud-gcp-506920` |
| Billing account | `012C25-4E479C-6B88C8` ("My Billing Account", open) linked to the project, billing enabled |
| BigQuery API | enabled (incl. `bigquerydatatransfer` — the API the export pipeline uses) |
| Billing export dataset | **NOT configured** — `bq ls` shows no datasets; no export table exists |
| Application Default Credentials | present (`~/.config/gcloud/application_default_credentials.json`, from `gcloud auth application-default login`) |
| Service account keys on disk | none found / none referenced by this project |

**Conclusion:** the integration is code-complete (provider, config, tests) but
dormant: `DEMO_MODE=true` keeps everything local. Real data requires the
manual steps in §2 — a human decision with a billing impact.

## 2. Enabling the billing export (manual, one-time)

1. Cloud Console → **Billing** → *My Billing Account* → **Billing export** →
   *BigQuery details* → **Edit settings**.
2. Choose the project `learn-cloud-gcp-506920`, create/select dataset
   `cloud_cost_lab_billing`, enable **Detailed usage cost**.
3. Wait for the first daily job (data appears within ~a day; the table is
   named like `gcp_billing_export_v1_012C25...`).
4. Fill the `.env` values (see `docs/gcp-billing.md`) and set
   `DEMO_MODE=false`.

## 3. Permissions (least privilege, CLAUDE.md §37)

| Identity | Role | Why |
| --- | --- | --- |
| Human/ADC user running the API | `roles/bigquery.dataViewer` on the export dataset + `roles/bigquery.jobUser` on the project | read the export table, run queries — nothing more |
| Future service account (optional) | same two roles, dedicated `cost-data-reader` SA | separates the pipeline identity from the human identity |
| NOT granted | `roles/editor`, `roles/owner`, billing-admin | least privilege — the platform is read-only |

## 4. Authentication: WIF preferred, ADC locally, no key files

- **Local development:** Application Default Credentials (already present).
- **Deployment:** Workload Identity Federation where feasible (§8, §36) —
  short-lived tokens, no downloadable keys.
- **Never:** service-account JSON keys in files or git (`.gitignore` blocks
  `*service-account*.json` and friends; Gitleaks scans CI in Phase 12+).

## 5. Cost & security risk assessment (§7 checklist)

| Question | Answer |
| --- | --- |
| Billable resources created by this phase? | **None.** The export itself is a free configuration; BigQuery storage of the export is free for the first 90 days per table partition, then standard storage (~$0.02/GB/mo — a small lab's export is a few MB). Queries cost ~$5/TB scanned; this platform's queries scan a few MB (partition + column filtered, dry-run logged). |
| Cost risk | Unbounded ad-hoc queries by OTHER tools, not this one. This platform caps rows, caps days, filters partitions, and dry-run-logs bytes. |
| Security risk | Read-only scope; no PII beyond billing metadata; labels may contain team names. Dataset access should stay restricted (`dataViewer` only). |
| Destroy / disable | Turn off export: Billing → Billing export → **Disable**. Remove storage: `bq rm -r -f cloud_cost_lab_billing` (deletes the dataset — verify before running). Revert the platform: set `DEMO_MODE=true` and restart; the code path is identical. |

## 6. Verification checklist before switching to real mode

- [ ] Export table contains rows (`bq query` on one day, partition-filtered)
- [ ] `GCP_BILLING_*` values in `.env` match dataset/table
- [ ] Dry-run bytes logged look sane (MBs, not GBs)
- [ ] `GET /api/freshness` reports FRESH after the daily export job
- [ ] Recommendations/policies re-run cleanly on real data
- [ ] Budget amounts reviewed — real currency is now real money
