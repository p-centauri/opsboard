import type { ReactNode } from "react";

export interface BarItem {
  key: string;
  label: ReactNode;
  value: number;
  display: string;
}

/**
 * Horizontal bars as plain HTML: each row states its value in text, so the bar is
 * reinforcement, not the only carrier of the number. Single hue (magnitude).
 */
export function BarList({ items, label }: { items: BarItem[]; label: string }) {
  const max = Math.max(...items.map((i) => i.value), 0);
  return (
    <ul aria-label={label} className="space-y-3">
      {items.map((item) => (
        <li key={item.key}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate">{item.label}</span>
            <span className="shrink-0 font-medium">{item.display}</span>
          </div>
          <div className="h-2 rounded-full bg-surface-muted" aria-hidden="true">
            <div
              className="h-2 rounded-full bg-chart-1"
              style={{ width: max > 0 ? `${Math.max((item.value / max) * 100, item.value > 0 ? 2 : 0)}%` : 0 }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
