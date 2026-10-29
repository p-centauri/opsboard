import type { Metadata } from "next";

import { RequireRole } from "@/components/require-role";
import { PageHeader } from "@/components/ui/page-header";
import { ProductForm } from "../product-form";

export const metadata: Metadata = { title: "New product" };

export default function NewProductPage() {
  return (
    <div className="max-w-2xl">
      <PageHeader title="New product" back={{ href: "/products", label: "Products" }} />
      <RequireRole role="manager" back={{ href: "/products", label: "Back to products" }}>
        <ProductForm />
      </RequireRole>
    </div>
  );
}
