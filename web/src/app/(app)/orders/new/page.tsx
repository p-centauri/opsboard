import type { Metadata } from "next";

import { OrderForm } from "@/components/orders/order-form";
import { RequireRole } from "@/components/require-role";
import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = { title: "New order" };

export default function NewOrderPage() {
  return (
    <>
      <PageHeader title="New order" description="Orders start as drafts. Stock is reserved when you confirm." back={{ href: "/orders", label: "Orders" }} />
      <RequireRole role="manager" back={{ href: "/orders", label: "Back to orders" }}>
        <OrderForm />
      </RequireRole>
    </>
  );
}
