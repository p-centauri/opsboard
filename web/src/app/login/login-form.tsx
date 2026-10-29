"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/feedback";
import { Field, Input } from "@/components/ui/field";
import { isApiError } from "@/lib/api";
import { useLogin } from "@/lib/queries";
import { safeNext } from "@/lib/roles";

const schema = z.object({
  email: z.string().trim().min(1, "Enter your email").pipe(z.email("Enter a valid email, like name@company.com")),
  password: z.string().min(1, "Enter your password"),
});
type Values = z.infer<typeof schema>;

const DEMO_ACCOUNTS = [
  { label: "Viewer", email: "viewer@demo.local", note: "read-only" },
  { label: "Manager", email: "manager@demo.local", note: "can edit orders" },
] as const;

function errorText(error: unknown): string {
  if (isApiError(error, "too_many_attempts")) return error.message;
  if (isApiError(error, "invalid_credentials")) return "That email and password don't match. Check them and try again.";
  if (isApiError(error)) return error.message;
  return "Couldn't sign in. Try again.";
}

export function LoginForm({ demoPassword }: { demoPassword: string | null }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useLogin();
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
  const { errors } = form.formState;

  const signIn = (values: Values) =>
    login.mutate(values, { onSuccess: () => router.replace(safeNext(searchParams.get("next"))) });

  return (
    <>
      {login.isError && (
        <div className="mt-6">
          <Notice tone="danger">{errorText(login.error)}</Notice>
        </div>
      )}

      <form className="mt-6 space-y-4" noValidate onSubmit={form.handleSubmit(signIn)}>
        <Field label="Email" error={errors.email?.message}>
          {(a11y) => <Input {...a11y} type="email" autoComplete="username" inputMode="email" {...form.register("email")} />}
        </Field>
        <Field label="Password" error={errors.password?.message}>
          {(a11y) => <Input {...a11y} type="password" autoComplete="current-password" {...form.register("password")} />}
        </Field>
        <Button type="submit" variant="primary" className="w-full" pending={login.isPending}>
          Sign in
        </Button>
      </form>

      {demoPassword && (
        <section className="mt-8 border-t border-line pt-6" aria-labelledby="demo-heading">
          <h2 id="demo-heading" className="text-sm font-semibold">
            Try the demo
          </h2>
          <p className="mt-1 text-sm text-muted">Sample data, reset regularly. No sign-up needed.</p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((account) => (
              <Button
                key={account.email}
                disabled={login.isPending}
                onClick={() => signIn({ email: account.email, password: demoPassword })}
                className="h-auto flex-col py-2"
              >
                <span>{account.label}</span>
                <span className="text-xs font-normal text-muted">{account.note}</span>
              </Button>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
