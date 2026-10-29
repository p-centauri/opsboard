"use client";

import Link from "next/link";

import { DataTable, type Column } from "@/components/ui/data-table";
import { Card, EmptyState, ErrorState, Notice, TableSkeleton } from "@/components/ui/feedback";
import { Field, Select } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import type { Schemas } from "@/lib/api";
import { formatDateTime, titleCase } from "@/lib/format";
import { useAudit, useMe } from "@/lib/queries";
import { can } from "@/lib/roles";
import { useUrlState } from "@/lib/url-state";

type Entry = Schemas["AuditEntryOut"];
const ENTITIES = ["order", "customer", "product", "user"] as const;
const PAGE_SIZE = 25;
const LINKS: Partial<Record<string, string>> = { order: "/orders", customer: "/customers", product: "/products" };

function show(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return `${value.length} item${value.length === 1 ? "" : "s"}`;
  if (typeof value === "object") return "…";
  return String(value);
}

/** "status: confirmed → shipped" for updates; the field list for creates. */
function Changes({ entry }: { entry: Entry }) {
  const rows = Object.entries(entry.diff);
  if (rows.length === 0) return <span className="text-muted">No field changes</span>;
  return (
    <ul className="space-y-0.5">
      {rows.map(([field, value]) => (
        <li key={field} className="break-words">
          <span className="text-muted">{field.replaceAll("_", " ")}:</span>{" "}
          {Array.isArray(value) && value.length === 2 && entry.action !== "create"
            ? `${show(value[0])} → ${show(value[1])}`
            : show(value)}
        </li>
      ))}
    </ul>
  );
}

const columns: Column<Entry>[] = [
  { key: "when", header: "When", mobile: "title", cell: (e) => formatDateTime(e.created_at) },
  { key: "who", header: "Who", cell: (e) => <span className="break-all">{e.user_email ?? "System"}</span> },
  {
    key: "what",
    header: "What",
    cell: (e) => {
      const base = LINKS[e.entity];
      const label = `${titleCase(e.entity)} #${e.entity_id}`;
      return (
        <span>
          {titleCase(e.action)}{" "}
          {base ? <Link href={`${base}/${e.entity_id}`} className="text-accent hover:underline">{label}</Link> : label}
        </span>
      );
    },
  },
  { key: "changes", header: "Changes", cell: (e) => <Changes entry={e} /> },
];

export function AuditLog() {
  const url = useUrlState();
  const me = useMe();
  const entity = url.get("entity");
  const audit = useAudit({ entity, page: url.page, page_size: PAGE_SIZE });

  if (!can(me.data, "admin")) {
    return (
      <>
        <PageHeader title="Audit log" />
        <Notice tone="info" title="Admins only" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Audit log"
        description="Every change, who made it and when. Newest first."
        actions={
          <Field label="Show" hideLabel className="w-40">
            {(a11y) => (
              <Select {...a11y} value={entity} onChange={(e) => url.set({ entity: e.target.value })}>
                <option value="">All changes</option>
                {ENTITIES.map((e) => <option key={e} value={e}>{titleCase(e)}s</option>)}
              </Select>
            )}
          </Field>
        }
      />
      <Card>
        {audit.isPending ? (
          <TableSkeleton label="Loading audit log" />
        ) : audit.isError ? (
          <ErrorState error={audit.error} onRetry={() => void audit.refetch()} title="Couldn't load the audit log" />
        ) : audit.data.items.length === 0 ? (
          <EmptyState title="Nothing recorded yet">Changes to orders, customers, products and users appear here.</EmptyState>
        ) : (
          <>
            <DataTable caption="Audit log" columns={columns} rows={audit.data.items} rowKey={(e) => e.id} stale={audit.isPlaceholderData} />
            <Pagination label="Audit log pages" page={url.page} pageSize={PAGE_SIZE} total={audit.data.total} onPage={(p) => url.set({ page: p === 1 ? null : String(p) })} />
          </>
        )}
      </Card>
    </>
  );
}
