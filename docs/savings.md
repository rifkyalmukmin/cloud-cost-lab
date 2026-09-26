# Savings Verification Workflow — Cloud Cost Lab (Phase 13)

> Status: Implemented · Date: 2026-09-13
> The lifecycle that separates an estimate from money actually saved: OPEN → APPROVED → IMPLEMENTED → VERIFIED (REJECTED branch), with before/after measurement and an append-only audit trail (CLAUDE.md §23).
> **Rule of the phase: simulated savings are never called realized.** A saving without an actual after-measurement stays *potential*, and verification refuses when data does not exist.

---

## 1. Potential vs realized — the distinction

| | Potential savings | Realized savings |
| --- | --- | --- |
| What | A rule's estimate from pre-change evidence | The measured reduction after the change |
| When | At recommendation time | Only after VERIFIED with actual data |
| Where | `recommendations.potential_savings` | `recommendations.realized_savings` |
| Can be negative? | No (it is an estimate of opportunity) | **Yes** — if costs went up, that is stored as measured |

The `/savings` page shows both side by side; the savings summary endpoint
reports them as different quantities.

## 2. Lifecycle

```text
OPEN ──approve──▶ APPROVED ──implement──▶ IMPLEMENTED ──verify──▶ VERIFIED
   └─reject──▶ REJECTED (terminal)
```

| Transition | Endpoint | Guard |
| --- | --- | --- |
| approve | `POST /api/recommendations/{id}/approve` | only from OPEN |
| reject | `POST /api/recommendations/{id}/reject` | only from OPEN |
| implement | `POST /api/recommendations/{id}/implement` | only from APPROVED; records `implemented_at` (default now; backfillable) |
| verify | `POST /api/recommendations/{id}/verify` | only from IMPLEMENTED; computes before/after |

Wrong source status → `409`. Unknown id → structured `404`. Every transition
appends an **audit log** row (actor, action, from→to, details, request id);
the table is append-only — the application never updates or deletes audit rows.

**Implement** records that the human performed the change themselves (the
platform has no execution capability). **Verify** records the measured
outcome.

## 3. Before/after calculation (actual data, when it exists)

`compute_realized_savings()` (`analytics/savings.py`):

- **before**: mean daily **net cost** of the 30 days ending the day before
  implementation;
- **after**: mean daily net cost of the up-to-30 days starting on the
  implementation day — at least **7 days** of after-data required;
- **realized_savings** = (before daily − after daily) × 30 — a
  monthly-equivalent rate derived from two *measured* rates;
- if fewer than 7 after-days exist (or none), realized = `None` and the verify
  endpoint returns **409**: savings stay potential until data exists;
- a **negative** realized value (post-change costs rose) is stored as
  measured — never clamped, never hidden;
- alternatively, a caller may supply `actual_cost_after` (an externally
  measured monthly cost, source `"reported"`) — used verbatim, labelled
  differently from data-derived numbers.

`GET /api/recommendations/savings` aggregates per status:

- `potential_savings` — OPEN + APPROVED estimates;
- `approved_savings` — approved estimate awaiting implementation;
- `implemented` / `verified` — counts + potential sums in each stage;
- `realized_savings` — sum over VERIFIED rows only (measured);
- `rejected_savings_foregone` — potential of REJECTED rows (the audit view).

## 4. UI — `/savings`

Five stage cards (Potential → Approved → Implemented → Verified → **Realized**,
the last highlighted), a per-status breakdown including the rejected-foregone
row, and an explanation of the verification math. The recommendation detail
page gained **Mark implemented** (APPROVED) and **Verify savings**
(IMPLEMENTED) buttons so the whole lifecycle is drivable from the UI.

## 5. Testing

`apps/api/tests/test_savings.py` (8 tests):

- **approval** — OPEN → APPROVED; double-approve → 409;
- **rejection** — OPEN → REJECTED; rejected rows cannot approve/implement/verify;
- **implementation** — APPROVED → IMPLEMENTED (with backfilled date); OPEN →
  IMPLEMENTED forbidden;
- **verification** — IMPLEMENTED → VERIFIED with realized savings equal to an
  independent recomputation from `data/mock/cost.json` (30-day windows,
  daily averages, ×30); before/after days reported; `verified_at` set;
- **before/after calculation** — matches dataset recomputation to the cent;
  **honesty**: no after-data → 409 and status stays IMPLEMENTED with realized
  null; negative realized stored as negative; reported-actual path labelled
  `"reported"`;
- **audit trail** — every transition logged (actor/action/from→to), newest
  first, append-only across the session.

## 6. Limitations

- Realized savings compare daily net-cost run-rates; causal attribution
  (was the change really the cause?) remains a human judgement — the platform
  supplies the measurement, not the proof.
- Scope-level findings (cost anomalies) have no single resource; their
  verification requires a reported value or future project-level windows.
- The demo dataset is date-anchored in the past, so a freshly implemented
  recommendation has no after-data — verification correctly refuses until a
  backfilled implementation date inside the data span is used (or real data
  arrives in Phase 8+ mode).
