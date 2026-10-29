"use client";

import { useQuery } from "@tanstack/react-query";
import { useId, useState, type ReactNode } from "react";

import { api, queryString } from "@/lib/api";
import { useDebounced } from "@/lib/use-debounced";
import { Spinner } from "./ui/button";
import { Field, Input } from "./ui/field";

interface SearchPickerProps<T> {
  label: string;
  placeholder: string;
  /** API list endpoint that accepts `q`, e.g. "/customers". */
  endpoint: string;
  render: (item: T) => ReactNode;
  itemKey: (item: T) => number;
  onPick: (item: T) => void;
  error?: string;
  /** Items that can't be picked again (e.g. products already on the order). */
  exclude?: Set<number>;
}

/**
 * Type to search, then pick from the results. The results are plain buttons in a list,
 * so they work with Tab/Enter and screen readers without a custom combobox.
 */
export function SearchPicker<T>({ label, placeholder, endpoint, render, itemKey, onPick, error, exclude }: SearchPickerProps<T>) {
  const [text, setText] = useState("");
  const q = useDebounced(text.trim());
  const resultsId = useId();
  const results = useQuery({
    queryKey: ["picker", endpoint, q],
    queryFn: ({ signal }) => api<{ items: T[] }>(`${endpoint}${queryString({ q, page_size: 8 })}`, { signal }),
    enabled: q.length > 0,
  });
  const items = (results.data?.items ?? []).filter((item) => !exclude?.has(itemKey(item)));

  return (
    <div>
      <Field label={label} error={error}>
        {(a11y) => (
          <Input
            {...a11y}
            type="search"
            value={text}
            placeholder={placeholder}
            autoComplete="off"
            aria-controls={resultsId}
            onChange={(e) => setText(e.target.value)}
          />
        )}
      </Field>
      <div id={resultsId} aria-live="polite" className="mt-2">
        {q && results.isFetching && !results.data && (
          <p className="flex items-center gap-2 text-sm text-muted">
            <Spinner /> Searching…
          </p>
        )}
        {q && results.isError && <p className="text-sm text-danger">Search failed. Try again.</p>}
        {q && results.data && items.length === 0 && <p className="text-sm text-muted">No matches for “{q}”.</p>}
        {items.length > 0 && (
          <ul className="divide-y divide-line overflow-hidden rounded-md border border-line" aria-label={`${label} results`}>
            {items.map((item) => (
              <li key={itemKey(item)}>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-surface-muted"
                  onClick={() => {
                    onPick(item);
                    setText("");
                  }}
                >
                  {render(item)}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
