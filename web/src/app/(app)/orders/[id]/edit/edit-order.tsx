"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { OrderForm } from "@/components/orders/order-form";
import { ButtonLink } from "@/components/ui/button";
import { Card, ErrorState, Notice, Skeleton } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { useMe, useOrder } from "@/lib/queries";
import { can } from "@/lib/roles";

export function EditOrder() {
  const id = Number(useParams<{ id: string }>().id);
  const order = useOrder(id);
  const me = useMe();
  // Bumped after a conflict to remount the form with the freshly loaded order.
  const [formKey, setFormKey] = useState(0);
  const [conflict, setConflict] = useState(false);
  const back = { href: `/orders/${id}`, label: "Back to order" };

  if (order.isPending) return <Skeleton className="h-96 w-full" />;
  if (order.isError) {
    return (
      <>
        <PageHeader title="Edit order" back={back} />
        <Card><ErrorState error={order.error} onRetry={() => void order.refetch()} /></Card>
      </>
    );
  }
  if (!can(me.data, "manager") || !order.data.editable) {
    return (
      <>
        <PageHeader title={`Edit ${order.data.number}`} back={back} />
        <Notice tone="info" title="This order can't be edited" action={<ButtonLink href={back.href} size="sm">View order</ButtonLink>}>
          {order.data.editable ? "Editing needs the manager role." : "Only draft orders can be edited."}
        </Notice>
      </>
    );
  }

  return (
    <>
      <PageHeader title={`Edit ${order.data.number}`} back={back} />
      {conflict && (
        <div className="mb-4">
          <Notice tone="warning" title="Someone else changed this order">
            The form now shows their version. Re-apply your changes and save again.
          </Notice>
        </div>
      )}
      <OrderForm
        key={formKey}
        order={order.data}
        onConflict={() => {
          setConflict(true);
          void order.refetch().then(() => setFormKey((k) => k + 1));
        }}
      />
    </>
  );
}
