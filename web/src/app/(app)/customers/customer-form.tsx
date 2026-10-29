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
import { useSaveCustomer } from "@/lib/queries";

// Mirrors the API's CustomerIn rules; the API still validates (this is for fast feedback).
const schema = z.object({
  name: z.string().trim().min(1, "Enter a name").max(200, "Use at most 200 characters"),
  email: z.string().trim().min(1, "Enter an email").pipe(z.email("Enter a valid email, like buyer@company.com")),
  country: z
    .string()
    .trim()
    .regex(/^[A-Za-z]{2}$/, "Use a 2-letter country code, like US or DE")
    .transform((v) => v.toUpperCase()),
});
type Values = z.input<typeof schema>;
const FIELDS = ["name", "email", "country"] as const;

export function CustomerForm({ customer }: { customer?: Schemas["CustomerDetail"] }) {
  const router = useRouter();
  const notify = useNotify();
  const save = useSaveCustomer(customer?.id);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values, unknown, z.output<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: customer?.name ?? "", email: customer?.email ?? "", country: customer?.country ?? "" },
  });
  const { errors } = form.formState;

  const submit = form.handleSubmit((values) => {
    setFormError(null);
    save.mutate(values, {
      onSuccess: (saved) => {
        notify(customer ? "Customer saved" : `${saved.name} added`);
        if (!customer) router.push(`/customers/${saved.id}`);
        else form.reset(values);
      },
      onError: (error) => setFormError(applyServerErrors(error, form.setError, FIELDS)),
    });
  });

  return (
    <Card className="p-4 sm:p-5">
      <form noValidate onSubmit={submit} className="space-y-4">
        {formError && <Notice tone="danger" title="Couldn't save">{formError}</Notice>}
        <Field label="Company name" error={errors.name?.message}>
          {(a11y) => <Input {...a11y} autoComplete="organization" {...form.register("name")} />}
        </Field>
        <Field label="Email" error={errors.email?.message}>
          {(a11y) => <Input {...a11y} type="email" inputMode="email" autoComplete="email" {...form.register("email")} />}
        </Field>
        <Field label="Country code" hint="2 letters, like US or DE" error={errors.country?.message} className="max-w-40">
          {(a11y) => <Input {...a11y} maxLength={2} autoComplete="country" className="uppercase" {...form.register("country")} />}
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          {!customer && <ButtonLink href="/customers">Cancel</ButtonLink>}
          <Button type="submit" variant="primary" pending={save.isPending} disabled={customer && !form.formState.isDirty}>
            {customer ? "Save changes" : "Add customer"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
