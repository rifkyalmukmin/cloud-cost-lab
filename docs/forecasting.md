# Forecasting — Cloud Cost Lab (Phase 7)

> Status: Implemented · Date: 2026-09-13
> 30-day cost projection: `GET /api/forecast` and the `/forecast` page.
> **Every forecast is an estimate with an explicit range** (CLAUDE.md §27) — expected value, lower/upper bounds and a confidence label. No exact-value claims, ever.

---

## 1. Method (start simple, §27)

Two methods run over the **daily net-cost series** (per filter scope):

1. **Moving average** — the level of the last 14 days, held flat.
2. **Linear trend** — ordinary least squares over the last 60 days (or all
   history if shorter), extrapolated forward.

The published `expected` blends both 50/50: the moving average damps the
linear extrapolation from running away, while the trend keeps the projection
rising/falling when the data clearly is. Both components are returned per
point (`moving_average`, `linear_trend`) so the blend is auditable.

## 2. Uncertainty and confidence

- Bounds come from the **linear-fit residual standard deviation**: an ~80%
  interval (`expected ± 1.28 σ`). The lower bound is floored at 0 (costs
  cannot be negative).
- The response carries the interval definition (`"80% (±1.28 residual
  sigma)"`), the per-method parameters (window, slope, R²) and a
  `confidence` label:

| Confidence | Rule (project-specific heuristic) |
| --- | --- |
| HIGH | ≥ 45 history days and relative residual σ/mean ≤ 0.35 |
| MEDIUM | ≥ 21 history days and σ/mean ≤ 0.6 |
| LOW | anything else — including a zero baseline |

## 3. Data handling

- The series is **calendar-continuous** from the first to the last day in the
  data; a missing day is a zero-cost day (§41-style data anchoring, never the
  wall clock). Forecast dates start the day **after** the last data day.
- **Zero baseline** (all-zero history): expected = 0 without division errors,
  confidence LOW — there is nothing to be confident about.
- **Insufficient data** (< 14 days): the response reports
  `sufficient_data: false` with a message and empty forecast — no invented
  numbers.
- Trend direction: increasing / decreasing / stable, judged by the slope
  against 0.5% of the mean daily cost.

## 4. API — `GET /api/forecast`

- `horizon_days` (7–90, default 30), filters `project_id`, `service`,
  `environment`, `region` (invalid → 422).
- Response: `sufficient_data`, `history_days`, `history` (start/end/daily
  average), `methods`, `trend`, `interval`, `confidence`, `forecast[]`
  (date, moving_average, linear_trend, expected, lower_bound,
  upper_bound) and `totals` (expected/lower/upper for the horizon).

## 5. UI — `/forecast`

- Summary cards: expected 30-day total, the range, the confidence and the
  trend direction (with the fitted slope).
- Chart: observed daily cost (solid) continuing into the dashed expected line
  with the shaded ~80% interval, and a "today (data)" reference line marking
  where observation ends.
- The method blend, R², interval definition and the estimate-not-guarantee
  caveat are printed under the chart.
- Insufficient data renders an honest "not enough data yet" state.

## 6. Testing

In `apps/api/tests/test_forecast_anomalies.py` (pure, synthetic series):

- **insufficient data** — < 14 days ⇒ `sufficient_data: false`, empty
  forecast, null confidence, no invented numbers;
- **zero baseline** — 60 zero days ⇒ expected 0, bounds 0, no explosion,
  confidence LOW;
- **normal trend** — flat 2.0/day ⇒ expected ≈ 2.0 daily, 30 points, trend
  "stable", confidence HIGH, totals ≈ 60;
- **increasing / decreasing trend** — slope captured (±1e-4), blend ends
  above/below the MA level, bounds always bracket the expectation, costs
  never negative;
- **missing values** — zeros injected into a flat series dampen but never
  explode the forecast;
- endpoint shape — dates start after the data end, 30 points default,
  `horizon_days` 6/91 → 422, bounds bracket expectations point-by-point,
  totals inside the summed range.
