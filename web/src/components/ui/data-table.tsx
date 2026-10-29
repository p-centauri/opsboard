import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  /** API sort field; makes the header a sort toggle. */
  sort?: string;
  /** In the mobile card layout: the card heading, or hidden. Default: a labelled detail row. */
  mobile?: "title" | "hide";
}

interface DataTableProps<T> {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  /** Current sort, e.g. "-created_at". */
  sort?: string;
  onSort?: (sort: string) => void;
  /** Dims the table while the next page/filter result loads (previous rows stay visible). */
  stale?: boolean;
}

function SortHeader({ label, field, sort, onSort }: { label: string; field: string; sort?: string; onSort: (s: string) => void }) {
  const active = sort === field || sort === `-${field}`;
  const descending = sort === `-${field}`;
  const next = active && !descending ? `-${field}` : field;
  return (
    <button
      type="button"
      onClick={() => onSort(next)}
      className="inline-flex min-h-9 items-center gap-1 font-medium hover:text-fg"
    >
      {label}
      <span aria-hidden="true" className={active ? "text-fg" : "text-line-strong"}>
        {active ? (descending ? "↓" : "↑") : "↕"}
      </span>
    </button>
  );
}

/**
 * A semantic table on wider screens, a stack of cards below `md` (no horizontal scrolling
 * on phones). The hidden layout is display:none, so assistive tech reads only one.
 */
export function DataTable<T>({ caption, columns, rows, rowKey, sort, onSort, stale = false }: DataTableProps<T>) {
  const title = columns.find((c) => c.mobile === "title");
  const details = columns.filter((c) => c.mobile !== "title" && c.mobile !== "hide");
  return (
    <div aria-busy={stale || undefined} className={stale ? "opacity-60 transition-opacity" : "transition-opacity"}>
      <table className="hidden w-full text-sm md:table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line text-left text-muted">
            {columns.map((col) => {
              const active = col.sort && (sort === col.sort || sort === `-${col.sort}`);
              return (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={active ? (sort?.startsWith("-") ? "descending" : "ascending") : undefined}
                  className={`px-4 py-2 font-medium ${col.align === "right" ? "text-right" : ""}`}
                >
                  {col.sort && onSort ? (
                    <SortHeader label={col.header} field={col.sort} sort={sort} onSort={onSort} />
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b border-line last:border-0 hover:bg-surface-muted/60">
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 align-middle ${col.align === "right" ? "text-right" : ""}`}>
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <ul className="divide-y divide-line md:hidden" aria-label={caption}>
        {rows.map((row) => (
          <li key={rowKey(row)} className="px-4 py-3">
            {title && <div className="mb-2 font-medium">{title.cell(row)}</div>}
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
              {details.map((col) => (
                <div key={col.key} className="contents">
                  <dt className="text-muted">{col.header}</dt>
                  <dd className="min-w-0 text-right break-words">{col.cell(row)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  );
}
