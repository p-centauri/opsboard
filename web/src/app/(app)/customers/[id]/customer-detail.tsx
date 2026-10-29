"use client";

import { useParams } from "next/navigation";

import { ButtonLink } from "@/components/ui/button";
import { Card, ErrorState, Skeleton } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { formatDay, formatInt, formatMoney } from "@/lib/format";
import { useCustomer, useMe } from "@/lib/queries";
import { can } from "@/lib/roles";
import { CustomerForm } from "../customer-form";

export function CustomerDetail() {
  const id = Number(useParams<{ id: string }>().id);
  const customer = useCustomer(id);
  const me = useMe();
  const back = { href: "/customers", label: "Customers" };

  if (customer.isPending) return <Skeleton className="h-96 w-full" />;
  if (customer.isError) {
    return (
      <>
        <PageHeader title="Customer" back={back} />
        <Card><ErrorState error={customer.error} onRetry={() => void customer.refetch()} /></Card>
      </>
    );
  }
  const c = customer.data;
  return (
    <>
      <PageHeader
        title={c.name}
        description={`Customer since ${formatDay(c.created_at)}`}
        back={back}
        actions={<ButtonLink href={`/orders?customer_id=${c.id}`}>View orders</ButtonLink>}
      />
      <dl className="mb-6 grid grid-cols-2 gap-3 sm:max-w-md">
        <div className="rounded-lg border border-line bg-surface p-4">
          <dt className="text-sm text-muted">Orders</dt>
          <dd className="mt-1 text-xl font-semibold">{formatInt(c.order_count)}</dd>
        </div>
        <div className="rounded-lg border border-line bg-surface p-4">
          <dt className="text-sm text-muted">Lifetime value</dt>
          <dd className="mt-1 text-xl font-semibold">{formatMoney(c.lifetime_value)}</dd>
        </div>
      </dl>
      {can(me.data, "manager") ? (
        <>
          <h2 className="mb-3 text-base font-semibold">Details</h2>
          <CustomerForm key={c.id} customer={c} />
        </>
      ) : (
        <Card className="p-4 sm:p-5">
          <dl className="grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
            <dt className="text-muted">Email</dt>
            <dd className="break-all">{c.email}</dd>
            <dt className="text-muted">Country</dt>
            <dd>{c.country}</dd>
          </dl>
        </Card>
      )}
    </>
  );
}
