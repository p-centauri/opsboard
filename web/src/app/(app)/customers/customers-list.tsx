"use client";

import Link from "next/link";

import { Button, ButtonLink } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { Card, EmptyState, ErrorState, TableSkeleton } from "@/components/ui/feedback";
import { SearchFilter } from "@/components/ui/filter-bar";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import type { Schemas } from "@/lib/api";
import { formatDay } from "@/lib/format";
import { useCustomers, useMe } from "@/lib/queries";
import { can } from "@/lib/roles";
import { useUrlState } from "@/lib/url-state";

const PAGE_SIZE = 25;

const columns: Column<Schemas["CustomerOut"]>[] = [
  {
    key: "name",
    header: "Name",
    sort: "name",
    mobile: "title",
    cell: (c) => (
      <Link href={`/customers/${c.id}`} className="font-medium text-accent hover:underline">
        {c.name}
      </Link>
    ),
  },
  { key: "email", header: "Email", cell: (c) => <span className="break-all">{c.email}</span> },
  { key: "country", header: "Country", cell: (c) => c.country },
  { key: "created", header: "Customer since", sort: "created_at", cell: (c) => formatDay(c.created_at) },
];

export function CustomersList() {
  const url = useUrlState();
  const me = useMe();
  const q = url.get("q");
  const sort = url.get("sort") || "name";
  const customers = useCustomers({ q, sort, page: url.page, page_size: PAGE_SIZE });

  return (
    <>
      <PageHeader
        title="Customers"
        actions={can(me.data, "manager") && <ButtonLink href="/customers/new" variant="primary">New customer</ButtonLink>}
      />
      <Card>
        <div className="border-b border-line p-4">
          <SearchFilter label="Search" placeholder="Name or email" value={q} onChange={(v) => url.set({ q: v })} />
        </div>
        {customers.isPending ? (
          <TableSkeleton label="Loading customers" />
        ) : customers.isError ? (
          <ErrorState error={customers.error} onRetry={() => void customers.refetch()} title="Couldn't load customers" />
        ) : customers.data.items.length === 0 ? (
          q ? (
            <EmptyState title={`No customers match “${q}”`} action={<Button onClick={() => url.set({ q: null })}>Clear search</Button>} />
          ) : (
            <EmptyState title="No customers yet" />
          )
        ) : (
          <>
            <DataTable
              caption="Customers"
              columns={columns}
              rows={customers.data.items}
              rowKey={(c) => c.id}
              sort={sort}
              onSort={(next) => url.set({ sort: next === "name" ? null : next })}
              stale={customers.isPlaceholderData}
            />
            <Pagination label="Customer pages" page={url.page} pageSize={PAGE_SIZE} total={customers.data.total} onPage={(p) => url.set({ page: p === 1 ? null : String(p) })} />
          </>
        )}
      </Card>
    </>
  );
}
