"use client";

import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { ErrorState, Skeleton } from "@/components/ui/feedback";
import { useMe } from "@/lib/queries";

export default function AppLayout({ children }: { children: ReactNode }) {
  const me = useMe();

  if (me.isPending) {
    return (
      <div role="status" aria-label="Loading" className="min-h-dvh md:grid md:grid-cols-[15rem_1fr]">
        <div className="hidden border-r border-line bg-surface md:block" />
        <div className="space-y-4 px-4 py-6 sm:px-6 lg:px-8">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }
  if (me.isError) {
    // A 401 already redirected to /login (see providers.tsx); anything else is shown here.
    return (
      <main className="flex min-h-dvh items-center justify-center">
        <ErrorState error={me.error} onRetry={() => void me.refetch()} title="Couldn't load your account" />
      </main>
    );
  }
  return <AppShell user={me.data}>{children}</AppShell>;
}
