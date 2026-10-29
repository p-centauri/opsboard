"use client";

import { useState } from "react";

import { DataTable, type Column } from "@/components/ui/data-table";
import { Card, EmptyState, ErrorState, Notice, TableSkeleton } from "@/components/ui/feedback";
import { Select } from "@/components/ui/field";
import { useNotify } from "@/components/ui/notify";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Pill } from "@/components/ui/status-badge";
import { isApiError, type Role, type User } from "@/lib/api";
import { formatDay, titleCase } from "@/lib/format";
import { useMe, useUpdateUser, useUsers } from "@/lib/queries";
import { can } from "@/lib/roles";
import { useUrlState } from "@/lib/url-state";

const ROLES: Role[] = ["viewer", "manager", "admin"];
const PAGE_SIZE = 25;

function UserControls({ user, self }: { user: User; self: boolean }) {
  const update = useUpdateUser();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);

  if (self) return <span className="text-sm text-muted">That’s you</span>;

  const change = (body: { role?: Role; is_active?: boolean }, done: string) => {
    setError(null);
    update.mutate(
      { id: user.id, ...body },
      { onSuccess: () => notify(done), onError: (e) => setError(isApiError(e) ? e.message : "Couldn't update. Try again.") },
    );
  };

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <label className="sr-only" htmlFor={`role-${user.id}`}>
        Role for {user.email}
      </label>
      <Select
        id={`role-${user.id}`}
        className="!min-h-9 w-32"
        value={user.role}
        disabled={update.isPending}
        onChange={(e) => change({ role: e.target.value as Role }, `${user.email} is now ${e.target.value}`)}
      >
        {ROLES.map((r) => <option key={r} value={r}>{titleCase(r)}</option>)}
      </Select>
      <button
        type="button"
        className="min-h-9 rounded-md px-3 text-sm text-muted hover:bg-surface-muted hover:text-fg disabled:opacity-55"
        disabled={update.isPending}
        onClick={() => change({ is_active: !user.is_active }, `${user.email} ${user.is_active ? "deactivated" : "reactivated"}`)}
      >
        {user.is_active ? "Deactivate" : "Reactivate"}
      </button>
      {error && <p role="alert" className="w-full text-right text-sm text-danger">{error}</p>}
    </div>
  );
}

export function UsersAdmin() {
  const url = useUrlState();
  const me = useMe();
  const users = useUsers({ page: url.page, page_size: PAGE_SIZE });

  if (!can(me.data, "admin")) {
    return (
      <>
        <PageHeader title="Users" />
        <Notice tone="info" title="Admins only">Ask an admin if you need to change who has access.</Notice>
      </>
    );
  }

  const columns: Column<User>[] = [
    { key: "email", header: "Email", mobile: "title", cell: (u) => <span className="font-medium break-all">{u.email}</span> },
    { key: "status", header: "Status", cell: (u) => (u.is_active ? <Pill tone="success">Active</Pill> : <Pill>Deactivated</Pill>) },
    { key: "since", header: "Added", cell: (u) => formatDay(u.created_at) },
    { key: "actions", header: "Role and access", align: "right", cell: (u) => <UserControls user={u} self={u.id === me.data?.id} /> },
  ];

  return (
    <>
      <PageHeader title="Users" description="Role changes and deactivation sign the person out right away." />
      <Card>
        {users.isPending ? (
          <TableSkeleton label="Loading users" />
        ) : users.isError ? (
          <ErrorState error={users.error} onRetry={() => void users.refetch()} title="Couldn't load users" />
        ) : users.data.items.length === 0 ? (
          <EmptyState title="No users" />
        ) : (
          <>
            <DataTable caption="Users" columns={columns} rows={users.data.items} rowKey={(u) => u.id} stale={users.isPlaceholderData} />
            <Pagination label="User pages" page={url.page} pageSize={PAGE_SIZE} total={users.data.total} onPage={(p) => url.set({ page: p === 1 ? null : String(p) })} />
          </>
        )}
      </Card>
    </>
  );
}
