# Governance — Cloud Cost Lab (Phase 6)

> Status: Implemented · Date: 2026-09-13
> Advisory cost-guardrail policies: `GET /api/policies` and the `/policies` page.
> **A violation produces a warning, evidence, and audit information — never an automated action** (CLAUDE.md §34, §38). The platform has no infrastructure-modifying capability at all.

---

## 1. Design

Policies are declarative guardrails evaluated **at read time** against the
current data. Definitions (policy_id, name, description, config, enabled) live
in the `policies` table (migration 0003) and are idempotently seeded from
`POLICY_DEFINITIONS` in `costlab/governance/policies.py`; evaluation results
are never persisted, so they always reflect the latest data.

Result statuses (§32):

| Status | Meaning |
| --- | --- |
| `PASS` | no findings — every resource complies (or is verifiably out of scope) |
| `WARNING` | a governance gap or an **unverifiable** condition — worth fixing, not a breach |
| `VIOLATION` | a hard breach of a configured limit |

Evaluators are pure functions over `ResourceFact` rows (resource identity +
labels + trailing-30-day gross cost), which makes the boundary logic
unit-testable without a database.

## 2. The five policies

### REQUIRE_OWNER_LABEL
Resources without an owner attribute their cost as UNALLOCATED (§12 — never
guessed). Finding = the missing-attribution resource. Dataset result:
`vm-legacy-sandbox-1` → **WARNING**.

### REQUIRE_ENVIRONMENT_LABEL
Every resource must declare `environment` (in its labels) so policies can be
applied per environment. Dataset result: **PASS** (all 12 declare it).

### MAX_MONTHLY_COST
Config: `{"monthly_cost_usd": 10.0}`. A resource's trailing-30-day gross cost
**strictly above** the limit is a **VIOLATION**; exactly at the limit is
compliant (the strict boundary is unit-tested at 10.00 vs 10.01). Dataset
result: `sql-shop-orders-prod` ($17.27) → **VIOLATION**. Resources without
cost data cannot breach.

### NO_PUBLIC_DATABASE
Databases must not be publicly reachable. Evidence comes from data
(`public_ip` label): explicit `true` → **VIOLATION**, explicit
`false`/private → PASS, **no information → WARNING ("cannot verify")**.
An unverifiable control is never treated as compliant — that is the
security-relevant design decision of this policy. Dataset result: both Cloud
SQL instances lack reachability data → **WARNING**.

### DEV_RESOURCE_SCHEDULE
Development compute resources (VMs, Cloud SQL) should declare an off-hours
schedule label (e.g. `schedule=08:00-18:00-mon-fri`, §31); a missing schedule
is a **WARNING** (a scheduling opportunity, not a breach). Production is out
of scope by design. Dataset result: the three development resources →
**WARNING**.

## 3. Enforcement model — what a violation does

Exactly three things, per the phase constraints:

1. **Warning** — the status and summary appear in the API and the `/policies`
   page;
2. **Recommendation** — the finding detail states what to change and points to
   the human approval workflow (Phase 5 recommendations remain the action
   path);
3. **Audit information** — each finding records resource identity, the observed
   value vs the configured threshold, and the evaluation basis (trailing-30-day
   window), giving a reviewable trail.

No endpoint in this platform can stop, modify, or delete a cloud resource; the
policies layer adds no such capability.

## 4. API

- `GET /api/policies` — all enabled policies with `status`, `summary`,
  `config`, and `findings[]` (`resource_id`, `resource_name`, `detail`), plus a
  summary (`policy_count`, `by_status`, `finding_count`).
- Disabled policies are skipped; unknown policy definitions in the DB are
  ignored.

## 5. UI — `/policies`

Governance summary cards (PASS / WARNING / VIOLATION counts) and one card per
policy: description, status badge, summary, config line, and the finding list
with resource names/ids and the evidence detail. The unverifiable-database
caveat is printed on the page.

## 6. Testing

In `apps/api/tests/test_budget_governance.py`:

- strict MAX_MONTHLY_COST boundary (10.00 PASS / 10.01 VIOLATION / no-cost
  cannot breach);
- NO_PUBLIC_DATABASE never false-passes (true → VIOLATION, false → PASS,
  missing → WARNING, non-databases out of scope);
- label policies and DEV_RESOURCE_SCHEDULE (missing owner/env/schedule →
  WARNING; explicit values → PASS; production out of scope);
- dataset evaluation through the API: the exact five-policy outcome set
  (PASS 1 / WARNING 3 / VIOLATION 1, 7 findings) with pinned resource ids;
- response shape contains no action/executable fields — advisory only.

## 7. Limitations

- Policies are evaluated on read; at real scale a scheduled evaluator writing
  results + history (with an audit_logs table, §11) belongs in Phase 12+.
- `NO_PUBLIC_DATABASE` depends on provider data exposing reachability
  (Phase 9+); until then it warns instead of passing.
- Policies are platform-level config; per-team policy overrides are future work.
- Policy config is seeded from code; editing via API is deliberately out of
  scope for this phase.
