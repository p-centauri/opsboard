"use client";

import Link from "next/link";

import { Button, ButtonLink } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { Card, EmptyState, ErrorState, TableSkeleton } from "@/components/ui/feedback";
import { SearchFilter } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Pill } from "@/components/ui/status-badge";
import type { Schemas } from "@/lib/api";
import { formatInt, formatMoney } from "@/lib/format";
import { useMe, useProducts } from "@/lib/queries";
import { can } from "@/lib/roles";
import { useUrlState } from "@/lib/url-state";

const PAGE_SIZE = 25;

const columns: Column<Schemas["ProductOut"]>[] = [
  {
    key: "name",
    header: "Product",
    sort: "name",
    mobile: "title",
    cell: (p) => (
      <Link href={`/products/${p.id}`} className="font-medium text-accent hover:underline">
        {p.name}
      </Link>
    ),
  },
  { key: "sku", header: "SKU", sort: "sku", cell: (p) => <span className="font-mono text-xs">{p.sku}</span> },
  { key: "price", header: "Price", sort: "price", align: "right", cell: (p) => formatMoney(p.price) },
  {
    key: "stock",
    header: "In stock",
    sort: "stock_qty",
    align: "right",
    cell: (p) => (
      <span className="inline-flex items-center justify-end gap-2">
        {p.is_low_stock && <Pill tone="danger">Low</Pill>}
        {formatInt(p.stock_qty)}
      </span>
    ),
  },
];

export function ProductsList() {
  const url = useUrlState();
  const me = useMe();
  const q = url.get("q");
  const lowStock = url.get("low_stock") === "true";
  const sort = url.get("sort") || "name";
  const products = useProducts({ q, low_stock: lowStock || null, sort, page: url.page, page_size: PAGE_SIZE });
  const filtered = Boolean(q || lowStock);

  return (
    <>
      <PageHeader
        title="Products"
        actions={can(me.data, "manager") && <ButtonLink href="/products/new" variant="primary">New product</ButtonLink>}
      />
      <Card>
        <div className="flex flex-wrap items-end gap-4 border-b border-line p-4">
          <SearchFilter label="Search" placeholder="Name or SKU" value={q} onChange={(v) => url.set({ q: v })} />
          <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="size-4 accent-[var(--c-accent)]"
              checked={lowStock}
              onChange={(e) => url.set({ low_stock: e.target.checked ? "true" : null })}
            />
            Low stock only
          </label>
        </div>
        {products.isPending ? (
          <TableSkeleton label="Loading products" />
        ) : products.isError ? (
          <ErrorState error={products.error} onRetry={() => void products.refetch()} title="Couldn't load products" />
        ) : products.data.items.length === 0 ? (
          filtered ? (
            <EmptyState
              title={lowStock && !q ? "Nothing is low on stock" : "No products match these filters"}
              action={<Button onClick={() => url.set({ q: null, low_stock: null })}>Clear filters</Button>}
            />
          ) : (
            <EmptyState title="No products yet" />
          )
        ) : (
          <>
            <DataTable
              caption="Products"
              columns={columns}
              rows={products.data.items}
              rowKey={(p) => p.id}
              sort={sort}
              onSort={(next) => url.set({ sort: next === "name" ? null : next })}
              stale={products.isPlaceholderData}
            />
            <Pagination label="Product pages" page={url.page} pageSize={PAGE_SIZE} total={products.data.total} onPage={(p) => url.set({ page: p === 1 ? null : String(p) })} />
          </>
        )}
      </Card>
    </>
  );
}
