import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };
// Rendered per request so DEMO_PASSWORD is read at runtime, not baked in at build.
export const dynamic = "force-dynamic";

export default function LoginPage() {
  // Only set on the public demo, where these accounts are meant to be open to everyone.
  const demoPassword = process.env.DEMO_PASSWORD || null;
  return (
    <main className="flex min-h-dvh items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2">
          <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
            <rect width="32" height="32" rx="7" className="fill-accent" />
            <path d="M8 22V12m8 10V8m8 14v-6" className="stroke-on-accent" strokeWidth="3" strokeLinecap="round" />
          </svg>
          <span className="text-lg font-semibold">OpsBoard</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm text-muted">Orders, inventory and analytics in one place.</p>
        <Suspense>
          <LoginForm demoPassword={demoPassword} />
        </Suspense>
      </div>
    </main>
  );
}
