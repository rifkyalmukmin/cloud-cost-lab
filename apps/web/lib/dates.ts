export function formatIsoDate(
  value: string,
  options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" },
): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) {
    return value;
  }
  const local = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return local.toLocaleDateString("en-US", options);
}

export function formatIsoTimestamp(value: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}))?/.exec(value);
  if (!match) {
    return value;
  }
  const dateLabel = formatIsoDate(match[1], {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return match[2] ? `${dateLabel} ${match[2]}` : dateLabel;
}
