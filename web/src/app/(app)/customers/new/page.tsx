import type { Metadata } from "next";

import { RequireRole } from "@/components/require-role";
import { PageHeader } from "@/components/ui/page-header";
import { CustomerForm } from "../customer-form";

export const metadata: Metadata = { title: "New customer" };

export default function NewCustomerPage() {
  return (
    <div className="max-w-2xl">
      <PageHeader title="New customer" back={{ href: "/customers", label: "Customers" }} />
      <RequireRole role="manager" back={{ href: "/customers", label: "Back to customers" }}>
        <CustomerForm />
      </RequireRole>
    </div>
  );
}
