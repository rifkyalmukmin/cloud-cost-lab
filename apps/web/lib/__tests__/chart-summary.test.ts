import { describe, expect, it } from "vitest";

import { describeBreakdown, describeSeries } from "@/lib/chart-summary";

const usd = (value: number) => `$${value.toFixed(2)}`;

describe("describeSeries", () => {
  it("returns null for no data", () => {
    expect(describeSeries([], usd)).toBeNull();
  });

  it("reports range, min, max, latest and total", () => {
    const text = describeSeries(
      [
        { label: "2026-09-01", value: 2 },
        { label: "2026-09-02", value: 5 },
        { label: "2026-09-03", value: 1 },
      ],
      usd,
      "total",
    );
    expect(text).toBe(
      "3 points from 2026-09-01 to 2026-09-03. Minimum $1.00 on 2026-09-03. " +
        "Maximum $5.00 on 2026-09-02. Latest $1.00 on 2026-09-03. Total $8.00.",
    );
  });

  it("uses singular wording and average when asked", () => {
    expect(describeSeries([{ label: "a", value: 4 }], usd, "average")).toContain("1 point from a to a.");
    expect(
      describeSeries(
        [
          { label: "a", value: 2 },
          { label: "b", value: 4 },
        ],
        usd,
        "average",
      ),
    ).toContain("Average $3.00.");
  });
});

describe("describeBreakdown", () => {
  it("returns null for no rows", () => {
    expect(describeBreakdown([], usd)).toBeNull();
  });

  it("lists items with share and total", () => {
    const text = describeBreakdown(
      [
        { label: "Compute", value: 30, sharePct: 75 },
        { label: "SQL", value: 10, sharePct: 25 },
      ],
      usd,
    );
    expect(text).toBe("2 items, total $40.00. Breakdown: Compute $30.00 (75.0%); SQL $10.00 (25.0%).");
  });

  it("truncates to the top items and says how many are not listed", () => {
    const rows = Array.from({ length: 7 }, (_, i) => ({ label: `s${i}`, value: 10 - i }));
    const text = describeBreakdown(rows, usd, 3);
    expect(text).toContain("Top 3: s0 $10.00; s1 $9.00; s2 $8.00.");
    expect(text).toContain("4 more not listed.");
  });
});
