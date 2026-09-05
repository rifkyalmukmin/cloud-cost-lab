/** Number/date formatting for the dashboard. Values come from the API — these
 * helpers only shape how they are displayed. */

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatUsd(value: number): string {
  return usd.format(value);
}

export function formatPct(value: number, digits = 1): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

export function formatShare(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

/** Axis ticks: avoid duplicated rounded labels for small dollar values. */
export function formatAxisUsd(value: number): string {
  return `$${Number(value.toFixed(value >= 20 ? 0 : 1))}`;
}

/** "2026-09-05" -> "Sep 5, 2026" (UTC — the API speaks in dates, not timezones). */
export function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** "2026-09" -> "September 2026". */
export function formatMonthKey(monthKey: string): string {
  return new Date(`${monthKey}-01T00:00:00Z`).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}
