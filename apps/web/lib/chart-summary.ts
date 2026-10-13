/**
 * Text alternatives for charts. Every sentence is computed from the same data
 * the chart plots, so the screen-reader description cannot drift from it.
 */

export interface LabeledValue {
  label: string;
  value: number;
}

export type Formatter = (value: number) => string;

/**
 * Describe an ordered series: range of labels, min / max / latest and either
 * the total (additive values such as cost) or the average (ratios such as %).
 */
export function describeSeries(
  points: readonly LabeledValue[],
  format: Formatter,
  aggregate: "total" | "average" | "none" = "none",
): string | null {
  if (points.length === 0) return null;
  const first = points[0];
  const last = points[points.length - 1];
  let min = first;
  let max = first;
  let sum = 0;
  for (const point of points) {
    if (point.value < min.value) min = point;
    if (point.value > max.value) max = point;
    sum += point.value;
  }
  const parts = [
    `${points.length} ${points.length === 1 ? "point" : "points"} from ${first.label} to ${last.label}.`,
    `Minimum ${format(min.value)} on ${min.label}.`,
    `Maximum ${format(max.value)} on ${max.label}.`,
    `Latest ${format(last.value)} on ${last.label}.`,
  ];
  if (aggregate === "total") parts.push(`Total ${format(sum)}.`);
  if (aggregate === "average") parts.push(`Average ${format(sum / points.length)}.`);
  return parts.join(" ");
}

/** Describe a breakdown (largest first as served by the API): top items with
 * their value, optionally the share, and the grand total. */
export function describeBreakdown(
  rows: ReadonlyArray<LabeledValue & { sharePct?: number }>,
  format: Formatter,
  maxItems = 5,
): string | null {
  if (rows.length === 0) return null;
  const total = rows.reduce((acc, row) => acc + row.value, 0);
  const shown = rows.slice(0, maxItems).map((row) =>
    row.sharePct === undefined
      ? `${row.label} ${format(row.value)}`
      : `${row.label} ${format(row.value)} (${row.sharePct.toFixed(1)}%)`,
  );
  const hidden = rows.length - shown.length;
  return [
    `${rows.length} ${rows.length === 1 ? "item" : "items"}, total ${format(total)}.`,
    `${hidden > 0 ? `Top ${shown.length}` : "Breakdown"}: ${shown.join("; ")}.`,
    hidden > 0 ? `${hidden} more not listed.` : null,
  ]
    .filter((part): part is string => part !== null)
    .join(" ");
}
