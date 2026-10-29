"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, ButtonLink } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { Card, EmptyState, ErrorState, Notice, TableSkeleton } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/field";
import { SearchFilter } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError, queryString, type OrderStatus, type Schemas } from "@/lib/api";
import { formatDateTime, formatMoney, titleCase } from "@/lib/format";
import { useCustomer, useMe, useOrders } from "@/lib/queries";
import { can } from "@/lib/roles";
import { useUrlState } from "@/lib/url-state";

const STATUSES: OrderStatus[] = ["draft", "confirmed", "shipped", "delivered", "cancelled"];
const PAGE_SIZE = 25;

const columns: Column<Schemas["OrderSummary"]>[] = [
  {
    key: "number",
    header: "Order",
    sort: "number",
    mobile: "title",
    cell: (o) => (
      <Link href={`/orders/${o.id}`} className="font-medium whitespace-nowrap text-accent hover:underline">
        {o.number}
      </Link>
    ),
  },
  { key: "customer", header: "Customer", sort: "customer_name", cell: (o) => o.customer.name },
  { key: "status", header: "Status", sort: "status", cell: (o) => <StatusBadge status={o.status} /> },
  { key: "total", header: "Total", sort: "total", align: "right", cell: (o) => formatMoney(o.total) },
  { key: "created", header: "Created", sort: "created_at", cell: (o) => formatDateTime(o.created_at) },
];

/** Downloads through fetch so a refused export (too many rows) shows a message instead of a JSON file. */
function useCsvExport() {
  const [state, setState] = useState<{ pending: boolean; error: string | null }>({ pending: false, error: null });
  const run = async (query: string) => {
    setState({ pending: true, error: null });
    try {
      const response = await fetch(`/api/orders/export.csv${query}`, { credentials: "same-origin" });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
        throw new ApiError(response.status, "export_failed", body?.error?.message ?? "Export failed. Try again.");
      }
      const blob = await response.blob();
      const name = /filename="([^"]+)"/.exec(response.headers.get("content-disposition") ?? "")?.[1] ?? "orders.csv";
      const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: name });
      link.click();
      URL.revokeObjectURL(link.href);
      setState({ pending: false, error: null });
    } catch (error) {
      setState({ pending: false, error: error instanceof ApiError ? error.message : "Export failed. Check your connection." });
    }
  };
  return { ...state, run };
}

export function OrdersList() {
  const url = useUrlState();
  const me = useMe();
  const csv = useCsvExport();

  const customerId = url.get("customer_id");
  const customer = useCustomer(Number(customerId), Boolean(customerId));
  const filters = {
    customer_id: customerId,
    q: url.get("q"),
    status: url.getAll("status"),
    date_from: url.get("date_from"),
    date_to: url.get("date_to"),
  };
  const sort = url.get("sort") || "-created_at";
  const orders = useOrders({ ...filters, sort, page: url.page, page_size: PAGE_SIZE });
  const filtered = Boolean(filters.customer_id || filters.q || filters.status.length || filters.date_from || filters.date_to);
  const clearFilters = () => url.set({ customer_id: null, q: null, status: null, date_from: null, date_to: null });

  const toggleStatus = (status: OrderStatus, on: boolean) =>
    url.set({ status: on ? [...filters.status, status] : filters.status.filter((s) => s !== status) });

  return (
    <>
      <PageHeader
        title="Orders"
        actions={
          <>
            <Button pending={csv.pending} onClick={() => void csv.run(queryString(filters))}>
              Export CSV
            </Button>
            {can(me.data, "manager") && (
              <ButtonLink href="/orders/new" variant="primary">
                New order
              </ButtonLink>
            )}
          </>
        }
      />

      {csv.error && (
        <div className="mb-4">
          <Notice tone="danger" title="Couldn't export">{csv.error}</Notice>
        </div>
      )}

      <Card>
        <div className="space-y-4 border-b border-line p-4">
          {customerId && (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="rounded-full bg-accent-soft px-3 py-1">
                Customer: <span className="font-medium">{customer.data?.name ?? `#${customerId}`}</span>
              </span>
              <Button size="sm" variant="ghost" onClick={() => url.set({ customer_id: null })}>
                Show all customers
              </Button>
            </div>
          )}
          <div className="flex flex-wrap items-end gap-3">
            <SearchFilter label="Search" placeholder="Order number or customer" value={filters.q} onChange={(q) => url.set({ q })} />
            <Field label="From" className="w-full sm:w-40">
              {(a11y) => <Input {...a11y} type="date" value={filters.date_from} max={filters.date_to || undefined} onChange={(e) => url.set({ date_from: e.target.value })} />}
            </Field>
            <Field label="To" className="w-full sm:w-40">
              {(a11y) => <Input {...a11y} type="date" value={filters.date_to} min={filters.date_from || undefined} onChange={(e) => url.set({ date_to: e.target.value })} />}
            </Field>
          </div>
          <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <legend className="sr-only">Status</legend>
            <span className="text-sm font-medium" aria-hidden="true">Status</span>
            {STATUSES.map((status) => (
              <label key={status} className="inline-flex min-h-9 cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="size-4 accent-[var(--c-accent)]"
                  checked={filters.status.includes(status)}
                  onChange={(e) => toggleStatus(status, e.target.checked)}
                />
                {titleCase(status)}
              </label>
            ))}
            {filtered && (
              <Button size="sm" variant="ghost" className="ml-auto" onClick={clearFilters}>
                Clear filters
              </Button>
            )}
          </fieldset>
        </div>

        {orders.isPending ? (
          <TableSkeleton label="Loading orders" />
        ) : orders.isError ? (
          <ErrorState error={orders.error} onRetry={() => void orders.refetch()} title="Couldn't load orders" />
        ) : orders.data.items.length === 0 ? (
          filtered ? (
            <EmptyState
              title="No orders match these filters"
              action={<Button onClick={clearFilters}>Clear filters</Button>}
            />
          ) : (
            <EmptyState
              title="No orders yet"
              action={can(me.data, "manager") ? <ButtonLink href="/orders/new" variant="primary">Create the first order</ButtonLink> : undefined}
            />
          )
        ) : (
          <>
            <DataTable
              caption="Orders"
              columns={columns}
              rows={orders.data.items}
              rowKey={(o) => o.id}
              sort={sort}
              onSort={(next) => url.set({ sort: next === "-created_at" ? null : next })}
              stale={orders.isPlaceholderData}
            />
            <Pagination
              label="Orders pages"
              page={url.page}
              pageSize={PAGE_SIZE}
              total={orders.data.total}
              onPage={(page) => url.set({ page: page === 1 ? null : String(page) })}
            />
          </>
        )}
      </Card>
    </>
  );
}
