"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Button, ButtonLink } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Card, ErrorState, Notice, Skeleton } from "@/components/ui/feedback";
import { useNotify } from "@/components/ui/notify";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { isApiError, type OrderStatus, type Schemas } from "@/lib/api";
import { formatDateTime, formatInt, formatMoney } from "@/lib/format";
import { useMe, useOrder, useTransitionOrder } from "@/lib/queries";
import { can } from "@/lib/roles";

const ACTIONS: Record<OrderStatus, { label: string; done: string }> = {
  confirmed: { label: "Confirm order", done: "confirmed; stock reserved" },
  shipped: { label: "Mark as shipped", done: "marked as shipped" },
  delivered: { label: "Mark as delivered", done: "marked as delivered" },
  cancelled: { label: "Cancel order", done: "cancelled" },
  draft: { label: "Back to draft", done: "moved to draft" },
};

/** Maps "items.0.qty" style API fields to readable lines ("Bolt: Only 3 in stock"). */
function stockProblems(order: Schemas["OrderDetail"], fields: Record<string, string>): string[] {
  return Object.entries(fields).map(([key, message]) => {
    const index = Number(/^items\.(\d+)\./.exec(key)?.[1]);
    const item = Number.isInteger(index) ? order.items[index] : undefined;
    return item ? `${item.name} (${item.sku}): ${message}` : message;
  });
}

function OrderActions({ order }: { order: Schemas["OrderDetail"] }) {
  const notify = useNotify();
  const transition = useTransitionOrder(order.id);
  const [confirmCancel, setConfirmCancel] = useState(false);

  const run = (to: OrderStatus) =>
    transition.mutate(
      { to, version: order.version },
      { onSuccess: (saved) => { setConfirmCancel(false); notify(`${saved.number} ${ACTIONS[to].done}`); } },
    );

  const forward = order.allowed_transitions.filter((s) => s !== "cancelled");
  const canCancel = order.allowed_transitions.includes("cancelled");
  const error = transition.error;

  return (
    <>
      {error && (
        <div className="mb-4">
          {isApiError(error, "stale_version") ? (
            <Notice tone="warning" title="This order was changed by someone else">
              We’ve loaded the latest version. Check it and try again.
            </Notice>
          ) : isApiError(error, "insufficient_stock") ? (
            <Notice tone="danger" title="Not enough stock to confirm">
              <ul className="mt-1 list-disc pl-5">
                {stockProblems(order, error.fields).map((line) => <li key={line}>{line}</li>)}
              </ul>
            </Notice>
          ) : (
            <Notice tone="danger" title="That didn't work">{isApiError(error) ? error.message : "Try again."}</Notice>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {forward.map((to) => (
          <Button key={to} variant="primary" pending={transition.isPending && transition.variables?.to === to} disabled={transition.isPending} onClick={() => run(to)}>
            {ACTIONS[to].label}
          </Button>
        ))}
        {order.editable && <ButtonLink href={`/orders/${order.id}/edit`}>Edit</ButtonLink>}
        {canCancel && (
          <Button variant="danger" disabled={transition.isPending} onClick={() => setConfirmCancel(true)}>
            Cancel order
          </Button>
        )}
      </div>
      <ConfirmDialog
        open={confirmCancel}
        title={`Cancel ${order.number}?`}
        confirmLabel="Cancel order"
        destructive
        pending={transition.isPending}
        onConfirm={() => run("cancelled")}
        onClose={() => setConfirmCancel(false)}
      >
        {order.status === "confirmed"
          ? "Reserved stock goes back to inventory. A cancelled order can't be reopened."
          : "A cancelled order can't be reopened."}
      </ConfirmDialog>
    </>
  );
}

export function OrderDetail() {
  const id = Number(useParams<{ id: string }>().id);
  const order = useOrder(id);
  const me = useMe();

  if (order.isPending) {
    return (
      <div role="status" aria-label="Loading order" className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (order.isError) {
    return (
      <>
        <PageHeader title="Order" back={{ href: "/orders", label: "Orders" }} />
        <Card><ErrorState error={order.error} onRetry={() => void order.refetch()} title="Couldn't load this order" /></Card>
      </>
    );
  }

  const o = order.data;
  return (
    <>
      <PageHeader
        back={{ href: "/orders", label: "Orders" }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            {o.number} <StatusBadge status={o.status} />
          </span>
        }
        description={
          <>
            <Link href={`/customers/${o.customer.id}`} className="text-accent hover:underline">{o.customer.name}</Link>
            {" · "}Created {formatDateTime(o.created_at)} · Updated {formatDateTime(o.updated_at)}
          </>
        }
      />

      {can(me.data, "manager") && (o.allowed_transitions.length > 0 || o.editable) && (
        <div className="mb-6">
          <OrderActions order={o} />
        </div>
      )}

      <Card>
        <h2 className="border-b border-line px-4 py-3 text-base font-semibold">Items</h2>
        <table className="w-full text-sm">
          <caption className="sr-only">Items in {o.number}</caption>
          <thead>
            <tr className="border-b border-line text-left text-muted">
              <th scope="col" className="px-4 py-2 font-medium">Product</th>
              <th scope="col" className="px-4 py-2 text-right font-medium">Qty</th>
              <th scope="col" className="hidden px-4 py-2 text-right font-medium sm:table-cell">Unit price</th>
              <th scope="col" className="px-4 py-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {o.items.map((item) => (
              <tr key={item.id} className="border-b border-line">
                <td className="px-4 py-3">
                  <Link href={`/products/${item.product_id}`} className="font-medium hover:underline">{item.name}</Link>
                  <span className="block text-muted">{item.sku}<span className="sm:hidden"> · {formatMoney(item.unit_price)} each</span></span>
                </td>
                <td className="px-4 py-3 text-right">{formatInt(item.qty)}</td>
                <td className="hidden px-4 py-3 text-right sm:table-cell">{formatMoney(item.unit_price)}</td>
                <td className="px-4 py-3 text-right">{formatMoney(item.line_total)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2} className="px-4 py-3 text-left font-semibold sm:hidden">Order total</th>
              <th scope="row" colSpan={3} className="hidden px-4 py-3 text-left font-semibold sm:table-cell">Order total</th>
              <td className="px-4 py-3 text-right text-base font-semibold">{formatMoney(o.total)}</td>
            </tr>
          </tfoot>
        </table>
      </Card>
    </>
  );
}
