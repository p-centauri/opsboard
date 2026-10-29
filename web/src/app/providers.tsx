"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { isApiError } from "@/lib/api";
import { NotifyProvider } from "@/components/ui/notify";

/** Session expired or revoked mid-use: send the user to sign in, then back here. */
function redirectIfSignedOut(error: unknown) {
  if (!isApiError(error) || error.status !== 401) return;
  if (window.location.pathname === "/login") return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  // Deliberately a full page load (outside React, no router here): it also discards every
  // cached query from the signed-out session.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`/login?next=${next}`);
}

function retryable(failureCount: number, error: unknown): boolean {
  // Retry only what can succeed on retry: network blips and 5xx. Never 4xx.
  const transient = isApiError(error) && (error.status === 0 || error.status >= 500);
  return transient && failureCount < 2;
}

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({ onError: redirectIfSignedOut }),
        mutationCache: new MutationCache({ onError: redirectIfSignedOut }),
        defaultOptions: {
          queries: { staleTime: 30_000, retry: retryable },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <NotifyProvider>{children}</NotifyProvider>
    </QueryClientProvider>
  );
}
