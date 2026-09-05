import { describe, expect, it } from "vitest";

import type { TrendPoint } from "@/lib/api";
import { monthlyComparison, toMonthPosition } from "@/lib/metrics";

function dailyPoints(days: Array<[string, number]>): TrendPoint[] {
  return days.map(([period, cost]) => ({ period, cost, credits: 0, net_cost: cost }));
}

describe("toMonthPosition", () => {
  it("sums MTD cost and counts elapsed days", () => {
    const position = toMonthPosition(
      dailyPoints([
        ["2026-09-01", 2.0],
        ["2026-09-02", 2.5],
        ["2026-09-03", 2.5],
      ]),
    );
    expect(position).toEqual({ monthKey: "2026-09", mtdCost: 7, daysElapsed: 3, daysInMonth: 30 });
  });

  it("returns null for an empty month", () => {
    expect(toMonthPosition([])).toBeNull();
  });

  it("knows calendar month lengths", () => {
    const august = toMonthPosition(dailyPoints([["2026-08-01", 1]]));
    expect(august?.daysInMonth).toBe(31);
    const february = toMonthPosition(dailyPoints([["2027-02-01", 1]]));
    expect(february?.daysInMonth).toBe(28);
  });
});

describe("monthlyComparison", () => {
  const monthly = dailyPoints([
    ["2026-08-01", 61],
    ["2026-09-01", 12],
  ]);

  it("compares MTD against the same number of days in the previous month", () => {
    // September has 3 days of data (2+2+2 = 6); August 1–3 had 1+1+1.5 = 3.5.
    const daily = dailyPoints([
      ["2026-08-01", 1],
      ["2026-08-02", 1],
      ["2026-08-03", 1.5],
      ["2026-08-04", 9], // beyond the comparison window on purpose
      ["2026-09-01", 2],
      ["2026-09-02", 2],
      ["2026-09-03", 2],
    ]);
    const comparison = monthlyComparison(monthly, daily);
    expect(comparison?.current.mtdCost).toBeCloseTo(6);
    expect(comparison?.current.daysElapsed).toBe(3);
    expect(comparison?.previous.mtdCost).toBeCloseTo(3.5);
    expect(comparison?.momChangePct).toBeCloseTo(((6 - 3.5) / 3.5) * 100, 6);
  });

  it("projects month-end cost linearly from the run rate", () => {
    const daily = dailyPoints([
      ["2026-09-01", 2],
      ["2026-09-02", 2],
      ["2026-09-03", 2],
    ]);
    const comparison = monthlyComparison(monthly, daily);
    // 6 over 3 days -> 2/day * 30 days
    expect(comparison?.projectedCost).toBeCloseTo(60);
  });

  it("uses monthly totals as fallback when no daily points exist for the previous month", () => {
    const daily = dailyPoints([["2026-09-01", 3]]);
    const comparison = monthlyComparison(monthly, daily);
    expect(comparison?.previous.mtdCost).toBe(0);
    expect(comparison?.momChangePct).toBeNull();
  });

  it("returns null when fewer than two months exist", () => {
    expect(monthlyComparison(dailyPoints([["2026-09-01", 12]]), [])).toBeNull();
    expect(monthlyComparison([], [])).toBeNull();
  });

  it("sorts months by key, not by array order", () => {
    const shuffled = dailyPoints([
      ["2026-09-01", 12],
      ["2026-08-01", 61],
    ]);
    const daily = dailyPoints([
      ["2026-08-01", 2],
      ["2026-09-01", 3],
      ["2026-09-02", 3],
    ]);
    const comparison = monthlyComparison(shuffled, daily);
    expect(comparison?.current.monthKey).toBe("2026-09");
    expect(comparison?.previous.monthKey).toBe("2026-08");
  });
});
