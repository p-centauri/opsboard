"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SearchPicker } from "@/components/search-picker";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, Notice } from "@/components/ui/feedback";
import { Input } from "@/components/ui/field";
import { useNotify } from "@/components/ui/notify";
import { isApiError, type Schemas } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { useCreateOrder, useUpdateOrder } from "@/lib/queries";

export interface Line {
  product_id: number;
  sku: string;
  name: string;
  price: string;
  qty: string; // raw input; validated before submit
}

type CustomerRef = Schemas["CustomerRef"];
type Errors = Record<string, string>;

const MAX_QTY = 10_000;
const MAX_LINES = 100;

export function validateOrder(customer: CustomerRef | null, lines: Line[]): Errors {
  const errors: Errors = {};
  if (!customer) errors.customer_id = "Choose a customer";
  if (lines.length === 0) errors.items = "Add at least one product";
  if (lines.length > MAX_LINES) errors.items = `An order can have at most ${MAX_LINES} products`;
  lines.forEach((line, i) => {
    const qty = Number(line.qty);
    if (!Number.isInteger(qty) || qty < 1 || qty > MAX_QTY) errors[`items.${i}.qty`] = `Enter a whole number from 1 to ${MAX_QTY}`;
  });
  return errors;
}

function without(errors: Errors, key: string): Errors {
  const next = { ...errors };
  delete next[key];
  return next;
}

/** Estimate only: the server prices the order from current product prices. */
export function estimateTotal(lines: Line[]): number {
  return lines.reduce((sum, l) => sum + Number(l.price) * (Number.isInteger(Number(l.qty)) ? Number(l.qty) : 0), 0);
}

interface OrderFormProps {
  /** Present when editing a draft. */
  order?: Schemas["OrderDetail"];
  onConflict?: () => void;
}

export function OrderForm({ order, onConflict }: OrderFormProps) {
  const router = useRouter();
  const notify = useNotify();
  const create = useCreateOrder();
  const update = useUpdateOrder(order?.id ?? 0);
  const mutation = order ? update : create;

  const [customer, setCustomer] = useState<CustomerRef | null>(order?.customer ?? null);
  const [lines, setLines] = useState<Line[]>(
    order?.items.map((i) => ({ product_id: i.product_id, sku: i.sku, name: i.name, price: i.unit_price, qty: String(i.qty) })) ?? [],
  );
  const [errors, setErrors] = useState<Errors>({});

  const setQty = (index: number, qty: string) => setLines((all) => all.map((l, i) => (i === index ? { ...l, qty } : l)));
  const removeLine = (index: number) => setLines((all) => all.filter((_, i) => i !== index));

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const found = validateOrder(customer, lines);
    setErrors(found);
    if (Object.keys(found).length > 0 || !customer) return;
    const items = lines.map((l) => ({ product_id: l.product_id, qty: Number(l.qty) }));
    const onError = (error: unknown) => {
      if (isApiError(error, "stale_version")) onConflict?.();
      if (isApiError(error)) setErrors(error.fields);
    };
    if (order) {
      update.mutate(
        { version: order.version, customer_id: customer.id, items },
        { onError, onSuccess: (saved) => { notify(`${saved.number} saved`); router.push(`/orders/${saved.id}`); } },
      );
    } else {
      create.mutate(
        { customer_id: customer.id, items },
        { onError, onSuccess: (saved) => { notify(`${saved.number} created as a draft`); router.push(`/orders/${saved.id}`); } },
      );
    }
  };

  const serverError = mutation.isError && !isApiError(mutation.error, "stale_version") ? mutation.error : null;

  return (
    <form noValidate onSubmit={submit} className="space-y-4">
      {serverError && (
        <Notice tone="danger" title="Couldn't save the order">
          {isApiError(serverError) ? serverError.message : "Try again."}
        </Notice>
      )}

      <Card className="p-4 sm:p-5">
        <h2 className="mb-3 text-base font-semibold">Customer</h2>
        {customer ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-line px-3 py-2">
            <span className="font-medium">{customer.name}</span>
            <Button size="sm" variant="ghost" onClick={() => setCustomer(null)}>
              Change
            </Button>
          </div>
        ) : (
          <SearchPicker<Schemas["CustomerOut"]>
            label="Find a customer"
            placeholder="Name or email"
            endpoint="/customers"
            itemKey={(c) => c.id}
            error={errors.customer_id}
            render={(c) => (
              <>
                <span className="font-medium">{c.name}</span>
                <span className="truncate text-muted">{c.email}</span>
              </>
            )}
            onPick={(c) => {
              setCustomer({ id: c.id, name: c.name });
              setErrors((all) => without(all, "customer_id"));
            }}
          />
        )}
      </Card>

      <Card className="p-4 sm:p-5">
        <h2 className="mb-3 text-base font-semibold">Products</h2>
        {lines.length > 0 && (
          <ul className="mb-4 divide-y divide-line rounded-md border border-line" aria-label="Order lines">
            {lines.map((line, index) => {
              const qtyError = errors[`items.${index}.qty`] ?? errors[`items.${index}.product_id`];
              const qtyId = `qty-${line.product_id}`;
              return (
                <li key={line.product_id} className="flex flex-wrap items-start gap-3 px-3 py-3">
                  <div className="min-w-0 flex-1 basis-48">
                    <p className="font-medium break-words">{line.name}</p>
                    <p className="text-sm text-muted">
                      {line.sku} · {formatMoney(line.price)} each
                    </p>
                  </div>
                  <div className="w-28">
                    <label htmlFor={qtyId} className="sr-only">
                      Quantity of {line.name}
                    </label>
                    <Input
                      id={qtyId}
                      type="number"
                      inputMode="numeric"
                      min={1}
                      max={MAX_QTY}
                      step={1}
                      value={line.qty}
                      aria-invalid={Boolean(qtyError)}
                      aria-describedby={qtyError ? `${qtyId}-error` : undefined}
                      onChange={(e) => setQty(index, e.target.value)}
                    />
                    {qtyError && (
                      <p id={`${qtyId}-error`} role="alert" className="mt-1 text-xs text-danger">
                        {qtyError}
                      </p>
                    )}
                  </div>
                  <Button size="sm" variant="ghost" aria-label={`Remove ${line.name}`} onClick={() => removeLine(index)}>
                    Remove
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
        <SearchPicker<Schemas["ProductOut"]>
          label={lines.length ? "Add another product" : "Add a product"}
          placeholder="Product name or SKU"
          endpoint="/products"
          itemKey={(p) => p.id}
          exclude={new Set(lines.map((l) => l.product_id))}
          error={errors.items}
          render={(p) => (
            <>
              <span className="min-w-0">
                <span className="font-medium">{p.name}</span> <span className="text-muted">{p.sku}</span>
              </span>
              <span className="shrink-0 text-muted">
                {formatMoney(p.price)} · {p.stock_qty} in stock
              </span>
            </>
          )}
          onPick={(p) => {
            setLines((all) => [...all, { product_id: p.id, sku: p.sku, name: p.name, price: p.price, qty: "1" }]);
            setErrors((all) => without(all, "items"));
          }}
        />
      </Card>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted">
          Estimated total <span className="ml-1 text-base font-semibold text-fg">{formatMoney(estimateTotal(lines))}</span>
          <span className="block text-xs">Priced at current product prices when saved.</span>
        </p>
        <div className="flex gap-2">
          <ButtonLink href={order ? `/orders/${order.id}` : "/orders"}>Cancel</ButtonLink>
          <Button type="submit" variant="primary" pending={mutation.isPending}>
            {order ? "Save changes" : "Create draft"}
          </Button>
        </div>
      </div>
    </form>
  );
}
