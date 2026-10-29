import { describe, expect, it } from "vitest";

import { estimateTotal, validateOrder, type Line } from "@/components/orders/order-form";
import { parseRange, rangeDates, trendInterval } from "./date-range";
import { change, formatDay, formatMoney, formatMoneyWhole } from "./format";
import { can, safeNext } from "./roles";

describe("can", () => {
  it("ranks viewer < manager < admin", () => {
    expect(can({ role: "manager" }, "viewer")).toBe(true);
    expect(can({ role: "manager" }, "manager")).toBe(true);
    expect(can({ role: "manager" }, "admin")).toBe(false);
    expect(can(undefined, "viewer")).toBe(false);
  });
});

describe("safeNext (open-redirect guard)", () => {
  it.each([
    ["/orders?status=draft", "/orders?status=draft"],
    [null, "/"],
    ["", "/"],
    ["https://evil.example", "/"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["javascript:alert(1)", "/"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});

describe("rangeDates", () => {
  const today = new Date("2026-03-15T09:30:00Z");

  it("covers complete days ending yesterday (UTC)", () => {
    expect(rangeDates("7", today)).toEqual({ date_from: "2026-03-08", date_to: "2026-03-14" });
    expect(rangeDates("30", today)).toEqual({ date_from: "2026-02-13", date_to: "2026-03-14" });
  });

  it("uses UTC even late in the day in other time zones", () => {
    expect(rangeDates("7", new Date("2026-03-15T23:59:00Z")).date_to).toBe("2026-03-14");
    expect(rangeDates("7", new Date("2026-03-16T00:00:00Z")).date_to).toBe("2026-03-15");
  });

  it("falls back to 30 days for unknown values", () => {
    expect(parseRange("1000")).toBe("30");
    expect(parseRange("90")).toBe("90");
  });

  it("switches to weekly points beyond 90 days", () => {
    expect(trendInterval("90")).toBe("day");
    expect(trendInterval("365")).toBe("week");
  });
});

describe("format", () => {
  it("formats decimal strings as money", () => {
    expect(formatMoney("1234.5")).toBe("$1,234.50");
    expect(formatMoneyWhole("1649256.78")).toBe("$1,649,257");
  });

  it("shows calendar days in UTC", () => {
    expect(formatDay("2026-03-01")).toBe("Mar 1, 2026");
  });

  it("has no change without a baseline", () => {
    expect(change(10, 0)).toBeNull();
    expect(change(15, 10)).toBe(0.5);
  });
});

describe("order form rules", () => {
  const line = (qty: string, price = "2.50"): Line => ({ product_id: 1, sku: "A", name: "A", price, qty });

  it("requires a customer and at least one product", () => {
    expect(validateOrder(null, [])).toEqual({ customer_id: "Choose a customer", items: "Add at least one product" });
  });

  it.each(["0", "-1", "1.5", "", "abc", "10001"])("rejects qty %j", (qty) => {
    expect(validateOrder({ id: 1, name: "A" }, [line(qty)])).toHaveProperty("items.0.qty");
  });

  it("accepts a valid order", () => {
    expect(validateOrder({ id: 1, name: "A" }, [line("3")])).toEqual({});
  });

  it("estimates the total and ignores invalid quantities", () => {
    expect(estimateTotal([line("3"), { ...line("2", "0.40"), product_id: 2 }])).toBeCloseTo(8.3);
    expect(estimateTotal([line("x")])).toBe(0);
  });
});
