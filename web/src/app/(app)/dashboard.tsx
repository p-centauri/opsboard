"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { BarList } from "@/components/dashboard/bar-list";
import { KpiTile } from "@/components/dashboard/kpi-tile";
import { RevenueChart, RevenueTable } from "@/components/dashboard/revenue-chart";
import { Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/feedback";
import { Field, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { DEFAULT_RANGE, RANGE_OPTIONS, parseRange, rangeDates, rangeLabel, trendInterval } from "@/lib/date-range";
import { change, formatInt, formatMoney, formatMoneyWhole, formatPercent } from "@/lib/format";
import { useStatusBreakdown, useSummary, useTopProducts, useTrend } from "@/lib/queries";
import { useUrlState } from "@/lib/url-state";

function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </Card>
  );
}

function Kpis({ params, label }: { params: Record<string, string>; label: string }) {
  const summary = useSummary(params);
  if (summary.isPending) {
    return (
      <div role="status" aria-label="Loading key figures" className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-[7.25rem]" />)}
      </div>
    );
  }
  if (summary.isError) return <Card><ErrorState error={summary.error} onRetry={() => void summary.refetch()} /></Card>;
  const { current: now, previous: prev } = summary.data;
  const compared = `previous ${label.replace("last ", "")}`;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      <KpiTile label="Revenue" value={formatMoneyWhole(now.revenue)} delta={change(Number(now.revenue), Number(prev.revenue))} comparedTo={compared} />
      <KpiTile label="Orders" value={formatInt(now.orders)} delta={change(now.orders, prev.orders)} comparedTo={compared} />
      <KpiTile label="Avg. order value" value={formatMoney(now.avg_order_value)} delta={change(Number(now.avg_order_value), Number(prev.avg_order_value))} comparedTo={compared} />
      <KpiTile
        label="Cancellation rate"
        value={formatPercent(now.cancellation_rate)}
        delta={change(now.cancellation_rate, prev.cancellation_rate)}
        higherIsBetter={false}
        comparedTo={compared}
      />
      <KpiTile label="Low-stock products" value={formatInt(summary.data.low_stock_products)} href="/products?low_stock=true" />
    </div>
  );
}

function Trend({ params, interval }: { params: Record<string, string>; interval: "day" | "week" }) {
  const trend = useTrend({ ...params, interval });
  return (
    <Panel title="Revenue">
      {trend.isPending ? (
        <Skeleton className="h-64" />
      ) : trend.isError ? (
        <ErrorState error={trend.error} onRetry={() => void trend.refetch()} />
      ) : trend.data.points.every((p) => p.orders === 0) ? (
        <EmptyState title="No sales in this period">Try a longer date range.</EmptyState>
      ) : (
        <div aria-busy={trend.isPlaceholderData || undefined} className={trend.isPlaceholderData ? "opacity-60" : ""}>
          <RevenueChart points={trend.data.points} interval={trend.data.interval} />
          <details className="mt-3 text-sm">
            <summary className="inline-flex min-h-9 cursor-pointer items-center text-muted hover:text-fg">Show as table</summary>
            <div className="mt-2 max-h-72 overflow-y-auto">
              <RevenueTable points={trend.data.points} interval={trend.data.interval} />
            </div>
          </details>
        </div>
      )}
    </Panel>
  );
}

function Statuses({ params }: { params: Record<string, string> }) {
  const breakdown = useStatusBreakdown(params);
  return (
    <Panel
      title="Orders by status"
      action={<Link href={`/orders?date_from=${params.date_from}&date_to=${params.date_to}`} className="text-sm text-accent hover:underline">View orders</Link>}
    >
      {breakdown.isPending ? (
        <Skeleton className="h-48" />
      ) : breakdown.isError ? (
        <ErrorState error={breakdown.error} onRetry={() => void breakdown.refetch()} />
      ) : breakdown.data.every((s) => s.count === 0) ? (
        <EmptyState title="No orders in this period" />
      ) : (
        <BarList
          label="Orders by status"
          items={breakdown.data.map((s) => ({ key: s.status, label: <StatusBadge status={s.status} />, value: s.count, display: formatInt(s.count) }))}
        />
      )}
    </Panel>
  );
}

function TopProducts({ params }: { params: Record<string, string> }) {
  const top = useTopProducts({ ...params, limit: 5 });
  return (
    <Panel title="Top products by revenue">
      {top.isPending ? (
        <Skeleton className="h-48" />
      ) : top.isError ? (
        <ErrorState error={top.error} onRetry={() => void top.refetch()} />
      ) : top.data.length === 0 ? (
        <EmptyState title="No sales in this period" />
      ) : (
        <BarList
          label="Top products by revenue"
          items={top.data.map((p) => ({
            key: String(p.product_id),
            label: (
              <Link href={`/products/${p.product_id}`} className="hover:underline">
                {p.name} <span className="text-muted">· {formatInt(p.units)} units</span>
              </Link>
            ),
            value: Number(p.revenue),
            display: formatMoney(p.revenue),
          }))}
        />
      )}
    </Panel>
  );
}

export function Dashboard() {
  const url = useUrlState();
  const range = parseRange(url.get("range"));
  const params = rangeDates(range);
  const label = rangeLabel(range);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Complete days in UTC, up to yesterday. Revenue counts confirmed, shipped and delivered orders."
        actions={
          <Field label="Date range" hideLabel className="w-44">
            {(a11y) => (
              <Select {...a11y} value={range} onChange={(e) => url.set({ range: e.target.value === DEFAULT_RANGE ? null : e.target.value })}>
                {RANGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </Select>
            )}
          </Field>
        }
      />
      <div className="space-y-4">
        <Kpis params={params} label={label} />
        <Trend params={params} interval={trendInterval(range)} />
        {/* grid-cols-1 = minmax(0,1fr): long names truncate instead of widening the column. */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Statuses params={params} />
          <TopProducts params={params} />
        </div>
      </div>
    </>
  );
}
