export const RANGE_OPTIONS = [
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "365", label: "Last 12 months" },
] as const;

export type RangeValue = (typeof RANGE_OPTIONS)[number]["value"];
export const DEFAULT_RANGE: RangeValue = "30";

export function parseRange(value: string): RangeValue {
  return RANGE_OPTIONS.some((o) => o.value === value) ? (value as RangeValue) : DEFAULT_RANGE;
}

const isoDay = (d: Date) => d.toISOString().slice(0, 10);

/**
 * Inclusive UTC day range of complete days, ending yesterday. Including today would show a
 * partial day as a sudden drop and bias every period-over-period comparison downward.
 */
export function rangeDates(range: RangeValue, today = new Date()): { date_from: string; date_to: string } {
  const end = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - 1));
  const start = new Date(end);
  start.setUTCDate(end.getUTCDate() - (Number(range) - 1));
  return { date_from: isoDay(start), date_to: isoDay(end) };
}

/** Daily points up to 90 days; weekly beyond, so a year stays readable. */
export const trendInterval = (range: RangeValue): "day" | "week" => (Number(range) > 90 ? "week" : "day");

export const rangeLabel = (range: RangeValue): string =>
  RANGE_OPTIONS.find((o) => o.value === range)?.label.toLowerCase() ?? "";
