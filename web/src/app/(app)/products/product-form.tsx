"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button, ButtonLink } from "@/components/ui/button";
import { Card, Notice } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/field";
import { useNotify } from "@/components/ui/notify";
import type { Schemas } from "@/lib/api";
import { applyServerErrors } from "@/lib/form-errors";
import { useSaveProduct } from "@/lib/queries";

const quantity = (label: string) =>
  z
    .string()
    .trim()
    .regex(/^\d+$/, `Enter ${label} as a whole number`)
    .refine((v) => Number(v) <= 1_000_000, "Use at most 1,000,000");

// Mirrors ProductIn on the API. Money stays a string ("12.50") all the way to the server.
const schema = z.object({
  sku: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9-]{1,32}$/, "Use up to 32 letters, digits or dashes")
    .transform((v) => v.toUpperCase()),
  name: z.string().trim().min(1, "Enter a name").max(200, "Use at most 200 characters"),
  price: z
    .string()
    .trim()
    .regex(/^\d{1,10}(\.\d{1,2})?$/, "Enter a price like 12.50")
    .transform((v) => Number(v).toFixed(2)),
  stock_qty: quantity("stock"),
  low_stock_threshold: quantity("a threshold"),
});
type Input_ = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = ["sku", "name", "price", "stock_qty", "low_stock_threshold"] as const;

function toPayload(values: Output): Schemas["ProductIn"] {
  return { ...values, stock_qty: Number(values.stock_qty), low_stock_threshold: Number(values.low_stock_threshold) };
}

export function ProductForm({ product }: { product?: Schemas["ProductOut"] }) {
  const router = useRouter();
  const notify = useNotify();
  const save = useSaveProduct(product?.id);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Input_, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: {
      sku: product?.sku ?? "",
      name: product?.name ?? "",
      price: product?.price ?? "",
      stock_qty: product ? String(product.stock_qty) : "0",
      low_stock_threshold: product ? String(product.low_stock_threshold) : "10",
    },
  });
  const { errors, dirtyFields } = form.formState;

  const submit = form.handleSubmit((values) => {
    setFormError(null);
    const payload = toPayload(values);
    // Edits send only what changed (see useSaveProduct).
    const body = product
      ? Object.fromEntries(Object.entries(payload).filter(([key]) => dirtyFields[key as keyof Input_]))
      : payload;
    save.mutate(body, {
      onSuccess: (saved) => {
        notify(product ? "Product saved" : `${saved.name} added`);
        if (!product) router.push(`/products/${saved.id}`);
        else form.reset({ ...values, stock_qty: String(saved.stock_qty), low_stock_threshold: String(saved.low_stock_threshold) });
      },
      onError: (error) => setFormError(applyServerErrors(error, form.setError, FIELDS)),
    });
  });

  return (
    <Card className="p-4 sm:p-5">
      <form noValidate onSubmit={submit} className="space-y-4">
        {formError && <Notice tone="danger" title="Couldn't save">{formError}</Notice>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" error={errors.name?.message} className="sm:col-span-2">
            {(a11y) => <Input {...a11y} {...form.register("name")} />}
          </Field>
          <Field label="SKU" error={errors.sku?.message}>
            {(a11y) => <Input {...a11y} autoCapitalize="characters" className="font-mono uppercase" {...form.register("sku")} />}
          </Field>
          <Field label="Price (USD)" error={errors.price?.message}>
            {(a11y) => <Input {...a11y} inputMode="decimal" {...form.register("price")} />}
          </Field>
          <Field
            label="In stock"
            error={errors.stock_qty?.message}
            hint={product ? "Confirmed orders already reduced this. Only change it after a stock count." : undefined}
          >
            {(a11y) => <Input {...a11y} inputMode="numeric" {...form.register("stock_qty")} />}
          </Field>
          <Field label="Low-stock alert at" hint="Flag the product when stock falls to this level" error={errors.low_stock_threshold?.message}>
            {(a11y) => <Input {...a11y} inputMode="numeric" {...form.register("low_stock_threshold")} />}
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          {!product && <ButtonLink href="/products">Cancel</ButtonLink>}
          <Button type="submit" variant="primary" pending={save.isPending} disabled={product && !form.formState.isDirty}>
            {product ? "Save changes" : "Add product"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
