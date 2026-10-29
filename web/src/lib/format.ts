// Fixed locale: identical output on server and client, and in tests.
const LOCALE = "en-US";

const money = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD" });
const wholeMoney = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const compactMoney = new Intl.NumberFormat(LOCALE, {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});
const integer = new Intl.NumberFormat(LOCALE);
const percent = new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: 1 });
const day = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeZone: "UTC" });
const dateTime = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeStyle: "short" });

/** API money is a decimal string ("1234.50"); never do arithmetic on the float for storage. */
export const formatMoney = (value: string | number): string => money.format(Number(value));
/** Headline figures: cents add noise at this scale. */
export const formatMoneyWhole = (value: string | number): string => wholeMoney.format(Number(value));
export const formatMoneyCompact = (value: string | number): string => compactMoney.format(Number(value));
export const formatInt = (value: number): string => integer.format(value);
export const formatPercent = (ratio: number): string => percent.format(ratio);
/** A calendar day ("2026-03-01" or an ISO timestamp), shown in UTC like the API's date filters. */
export const formatDay = (value: string): string => day.format(new Date(value.length === 10 ? `${value}T00:00:00Z` : value));
/** A moment, shown in the viewer's time zone. */
export const formatDateTime = (value: string): string => dateTime.format(new Date(value));

/** Relative change between periods, or null when there's no baseline to compare with. */
export function change(current: number, previous: number): number | null {
  if (previous === 0) return null;
  return (current - previous) / previous;
}

export const titleCase = (value: string): string => value.charAt(0).toUpperCase() + value.slice(1);
