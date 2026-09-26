# Budget — Cloud Cost Lab (Phase 6)

> Status: Implemented · Date: 2026-09-13
> Monthly budgets with inclusive warning/critical thresholds: `GET /api/budget`, `POST /api/budget`, and the `/budget` page.
> **No automatic action:** reaching a threshold raises a status/alert — the platform never stops, downsizes, or deletes anything.

---

## 1. Model (CLAUDE.md §15)

A budget has: `id`, `name`, `scope` (`scope_type` + `scope_value`), `period`,
`limit`, `warning_threshold`, `critical_threshold`, and a **derived** `status`.
Stored in the `budgets` table (migration 0003). Demo seeding creates one
budget when none exists: *Lab monthly budget*, $50/month, 70/90.

- `scope_type = all` applies to every cost record; `project`, `service`, or
  `environment` scopes filter by `scope_value`.
- `period` is `monthly` in this phase.
- Thresholds are **percentages of the limit** (70 / 90 in the demo), validated
  to 0 < threshold < 100 with warning strictly below critical.
- `status` is computed at read time from current spend — never stored, so it
  always reflects the latest data.

## 2. Spend definition

- Spend = **net cost** (after credits) — what is actually paid.
- Evaluation month = the latest month **in the data**, anchored to the data
  like every other endpoint (never the wall clock).
- Derived values: `daily_average` (MTD ÷ days elapsed), `remaining`
  (limit − spend), `spend_percentage`, and `projected_month_end` — a **linear
  run-rate estimate** (`MTD ÷ days elapsed × days in month`), labelled as an
  estimate everywhere it appears.
- `forecast_over_budget` — the projected month-end exceeds the limit while the
  current status may still be HEALTHY (the demo dataset shows exactly this:
  ~$10.62 MTD = HEALTHY at 21%, but a ~$63.7 projection against the $50 limit).

## 3. Status bands — inclusive boundaries

```text
HEALTHY  spend <  warning_threshold            69% -> HEALTHY
WARNING  warning_threshold <= spend < critical 70% -> WARNING, 89% -> WARNING
CRITICAL critical_threshold <= spend < 100%    90% -> CRITICAL, 99% -> CRITICAL
EXCEEDED spend >= 100%                         100% -> EXCEEDED, 101% -> EXCEEDED
```

Exactly at a threshold is already in the next band (§15 lists Exceeded at
100%). The pure function `budget_status()` is unit-tested across the full
ladder 69/70/89/90/99/100/101, with custom thresholds, fractional values, and
a degenerate zero/negative limit (immediately EXCEEDED, though the API rejects
creating such a budget).

## 4. API

- `GET /api/budget` — all budgets with their evaluation, plus a summary
  (evaluation month, data end, per-status counts, count of budgets forecast
  over budget). No data → `status: null` fields, not fabricated zeros.
- `POST /api/budget` — create a budget. Validated server-side with Pydantic
  (`extra="forbid"`): positive limit, thresholds in (0, 100), warning strictly
  below critical, `scope_value` required unless scope `all`, `period=monthly`.
  Errors return `422`; rejected payloads create nothing. A data-only operation.

## 5. UI — `/budget`

- Budget cards: name/scope/limit, status badge, progress bar with warning and
  critical threshold markers, spend (MTD), remaining, daily average, and the
  projected month-end (amber when forecast-over-budget).
- Create form (`New budget`) posting to `POST /api/budget` with inline errors.
- The inclusive-threshold and estimate caveats are printed on the page.

## 6. Testing

`apps/api/tests/test_budget_governance.py`:

- threshold ladder 69/70/89/90/99/100/101 (default 70/90) and custom
  thresholds (50/80), fractional inclusivity (69.999 / 70.001), degenerate
  limits;
- API evaluation matches an independent recomputation from
  `data/mock/cost.json` (MTD net spend, evaluation month, days elapsed);
- every status band reachable through the API with clear-margin limits,
  and status always consistent with the pure function;
- project-scoped budget spend equals the recomputation for that project;
- `POST` validation matrix (11 bad payloads → 422, nothing created) plus a
  SQL-injection-shaped payload stored safely as opaque data (ORM parameters);
- CORS preflight allows POST from the configured origin and rejects unknown
  origins.
