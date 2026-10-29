"use client";

import { useEffect, useState } from "react";

import { useDebounced } from "@/lib/use-debounced";
import { Field, Input } from "./field";

/** Search box that updates the URL after typing pauses, and follows URL changes (back button, clear). */
export function SearchFilter({ value, onChange, label, placeholder }: { value: string; onChange: (v: string) => void; label: string; placeholder?: string }) {
  const [text, setText] = useState(value);
  const [lastValue, setLastValue] = useState(value);
  const debounced = useDebounced(text);

  // The URL changed from outside (back button, "Clear filters"): show it. Adjusting state
  // during render (not in an effect) avoids an extra render pass.
  if (value !== lastValue) {
    setLastValue(value);
    if (value !== text.trim()) setText(value);
  }

  useEffect(() => {
    if (debounced.trim() !== value) onChange(debounced.trim());
    // onChange identity changes with the URL; reacting to the typed value is what matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <Field label={label} className="min-w-0 flex-1 basis-56">
      {(a11y) => (
        <Input {...a11y} type="search" value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)} />
      )}
    </Field>
  );
}
