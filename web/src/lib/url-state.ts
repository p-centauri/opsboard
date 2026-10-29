"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useOptimistic, useTransition } from "react";

export type UrlPatch = Record<string, string | readonly string[] | null | undefined>;

/**
 * Filters, sort and page live in the URL: shareable, bookmarkable, and the back button works.
 * Any change other than the page itself resets to page 1.
 *
 * Reads are optimistic: a control shows its new value immediately, instead of snapping back
 * until the router has committed the new URL.
 */
export function useUrlState() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [params, setOptimisticParams] = useOptimistic(searchParams.toString());
  const [, startTransition] = useTransition();

  const current = useMemo(() => new URLSearchParams(params), [params]);
  const get = useCallback((key: string) => current.get(key) ?? "", [current]);
  const getAll = useCallback((key: string) => current.getAll(key), [current]);
  const page = Math.max(1, Number(current.get("page")) || 1);

  const set = useCallback(
    (patch: UrlPatch) => {
      const next = new URLSearchParams(params);
      for (const [key, value] of Object.entries(patch)) {
        next.delete(key);
        if (Array.isArray(value)) value.forEach((v) => next.append(key, v));
        else if (typeof value === "string" && value !== "") next.set(key, value);
      }
      if (!("page" in patch)) next.delete("page");
      const query = next.toString();
      startTransition(() => {
        setOptimisticParams(query);
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
      });
    },
    [params, pathname, router, setOptimisticParams],
  );

  return { get, getAll, page, set };
}
