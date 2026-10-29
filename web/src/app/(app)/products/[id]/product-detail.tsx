"use client";

import { useParams } from "next/navigation";

import { Card, ErrorState, Skeleton } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
import { Pill } from "@/components/ui/status-badge";
import { formatInt, formatMoney } from "@/lib/format";
import { useMe, useProduct } from "@/lib/queries";
import { can } from "@/lib/roles";
import { ProductForm } from "../product-form";

export function ProductDetail() {
  const id = Number(useParams<{ id: string }>().id);
  const product = useProduct(id);
  const me = useMe();
  const back = { href: "/products", label: "Products" };

  if (product.isPending) return <Skeleton className="h-96 w-full max-w-2xl" />;
  if (product.isError) {
    return (
      <>
        <PageHeader title="Product" back={back} />
        <Card><ErrorState error={product.error} onRetry={() => void product.refetch()} /></Card>
      </>
    );
  }
  const p = product.data;
  return (
    <div className="max-w-2xl">
      <PageHeader
        title={p.name}
        back={back}
        description={
          <span className="inline-flex flex-wrap items-center gap-2">
            <span className="font-mono">{p.sku}</span>
            {p.is_low_stock && <Pill tone="danger">Low stock</Pill>}
          </span>
        }
      />
      {can(me.data, "manager") ? (
        <ProductForm key={p.id} product={p} />
      ) : (
        <Card className="p-4 sm:p-5">
          <dl className="grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
            <dt className="text-muted">Price</dt>
            <dd>{formatMoney(p.price)}</dd>
            <dt className="text-muted">In stock</dt>
            <dd>{formatInt(p.stock_qty)}</dd>
            <dt className="text-muted">Low-stock alert at</dt>
            <dd>{formatInt(p.low_stock_threshold)}</dd>
          </dl>
        </Card>
      )}
    </div>
  );
}
