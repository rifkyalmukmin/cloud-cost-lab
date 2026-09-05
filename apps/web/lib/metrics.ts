/**
 * Derived metrics for the overview dashboard.
 *
 * Every input comes from the API (monthly/daily trend points); these are pure
 * display-level calculations — a simple month-to-date comparison and a linear
 * run-rate projection. They are heuristics: the UI must always label them as
 * estimates (CLAUDE.md §4: never present estimates as exact or realized).
 *
 * "Current month" means the latest month present in the data, NOT the wall
 * clock — the mock dataset is date-anchored (ADR-003), and billing data always
 * has freshness lag anyway.
 */

import type { TrendPoint } from "@/lib/api";

export interface MonthPosition {
  /** "2026-09" */
  monthKey: string;
  /** Cost recorded so far in that month. */
  mtdCost: number;
  /** Number of days with data inside the month. */
  daysElapsed: number;
  /** Total days in the calendar month. */
  daysInMonth: number;
}

export interface MonthlyComparison {
  current: MonthPosition;
  previous: MonthPosition;
  /** Month-over-month change of month-to-date vs the previous month's first
   * `daysElapsed` days, in percent. Negative = costs went down. */
  momChangePct: number | null;
  /** Linear run-rate projection of the current month's final cost. */
  projectedCost: number;
}

function monthKeyOf(isoDate: string): string {
  return isoDate.slice(0, 7);
}

function daysInCalendarMonth(year: number, monthIndex1to12: number): number {
  return new Date(Date.UTC(year, monthIndex1to12, 0)).getUTCDate();
}

export function toMonthPosition(points: TrendPoint[]): MonthPosition | null {
  if (points.length === 0) return null;
  const monthKey = monthKeyOf(points[0].period);
  const [year, month] = monthKey.split("-").map(Number);
  return {
    monthKey,
    mtdCost: points.reduce((sum, p) => sum + p.cost, 0),
    daysElapsed: points.length,
    daysInMonth: daysInCalendarMonth(year, month),
  };
}

/** Latest two months (by month key) from monthly trend points. */
export function lastTwoMonthlyMonths(points: TrendPoint[]): { current: TrendPoint; previous: TrendPoint } | null {
  if (points.length < 2) return null;
  const sorted = [...points].sort((a, b) => a.period.localeCompare(b.period));
  return { previous: sorted[sorted.length - 2], current: sorted[sorted.length - 1] };
}

/**
 * Compare the latest month against the previous month over the same number of
 * elapsed days (MTD vs prior MTD) — a partial month compared to a full month
 * would produce a misleading "drop".
 */
export function monthlyComparison(
  monthlyPoints: TrendPoint[],
  dailyPoints: TrendPoint[],
): MonthlyComparison | null {
  const months = lastTwoMonthlyMonths(monthlyPoints);
  if (!months) return null;

  const currentKey = monthKeyOf(months.current.period);
  const previousKey = monthKeyOf(months.previous.period);
  const currentDaily = dailyPoints.filter((p) => monthKeyOf(p.period) === currentKey);
  const previousDaily = dailyPoints.filter((p) => monthKeyOf(p.period) === previousKey);
  const current = toMonthPosition(currentDaily);
  if (!current || current.daysElapsed === 0) return null;

  const priorSlice = previousDaily.slice(0, current.daysElapsed);
  const previous = toMonthPosition(priorSlice);

  const projectedCost = (current.mtdCost / current.daysElapsed) * current.daysInMonth;

  return {
    current,
    previous:
      previous ??
      ({
        monthKey: previousKey,
        mtdCost: 0,
        daysElapsed: current.daysElapsed,
        daysInMonth: 0,
      } satisfies MonthPosition),
    momChangePct:
      previous && previous.mtdCost > 0
        ? ((current.mtdCost - previous.mtdCost) / previous.mtdCost) * 100
        : null,
    projectedCost,
  };
}
