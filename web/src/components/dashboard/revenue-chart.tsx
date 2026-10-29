"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Schemas } from "@/lib/api";
import { formatDay, formatInt, formatMoney, formatMoneyCompact } from "@/lib/format";

type Point = Schemas["TrendPoint"];

const shortDay = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const tickDay = (iso: string) => shortDay.format(new Date(`${iso}T00:00:00Z`));

// Only the fields we read; Recharts' own generic tooltip types don't narrow to our row type.
interface TooltipProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: unknown }>;
  interval: string;
}

function ChartTooltip({ active, payload, interval }: TooltipProps) {
  const point = payload?.[0]?.payload as Point | undefined;
  if (!active || !point) return null;
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm shadow-md">
      <p className="text-muted">
        {interval === "week" ? "Week of " : ""}
        {formatDay(point.bucket)}
      </p>
      <p className="font-semibold">{formatMoney(point.revenue)}</p>
      <p className="text-muted">{formatInt(point.orders)} orders</p>
    </div>
  );
}

/** Single series, so no legend: the card title names it. A table view sits below for a11y. */
export function RevenueChart({ points, interval }: { points: Point[]; interval: string }) {
  const data = points.map((p) => ({ ...p, value: Number(p.revenue) }));
  return (
    <div className="h-64 w-full" role="img" aria-label="Revenue over time. The data is also available as a table below.">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--c-line)" />
          <XAxis
            dataKey="bucket"
            tickFormatter={tickDay}
            tick={{ fill: "var(--c-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "var(--c-line)" }}
            minTickGap={24}
          />
          <YAxis
            tickFormatter={(v: number) => formatMoneyCompact(v)}
            tick={{ fill: "var(--c-muted)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={56}
          />
          <Tooltip
            content={(props) => <ChartTooltip {...props} interval={interval} />}
            cursor={{ stroke: "var(--c-line-strong)", strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="var(--c-chart-1)"
            strokeWidth={2}
            fill="var(--c-chart-1)"
            fillOpacity={0.12}
            activeDot={{ r: 5, stroke: "var(--c-surface)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RevenueTable({ points, interval }: { points: Point[]; interval: string }) {
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">Revenue by {interval}</caption>
      <thead>
        <tr className="border-b border-line text-left text-muted">
          <th scope="col" className="py-1.5 font-medium">{interval === "week" ? "Week of" : "Day"}</th>
          <th scope="col" className="py-1.5 text-right font-medium">Orders</th>
          <th scope="col" className="py-1.5 text-right font-medium">Revenue</th>
        </tr>
      </thead>
      <tbody>
        {points.map((p) => (
          <tr key={p.bucket} className="border-b border-line last:border-0">
            <td className="py-1.5">{formatDay(p.bucket)}</td>
            <td className="py-1.5 text-right">{formatInt(p.orders)}</td>
            <td className="py-1.5 text-right">{formatMoney(p.revenue)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
