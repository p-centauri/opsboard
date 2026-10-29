import type { OrderStatus } from "@/lib/api";
import { titleCase } from "@/lib/format";

const styles: Record<OrderStatus, string> = {
  draft: "bg-neutral-soft text-muted",
  confirmed: "bg-info-soft text-info",
  shipped: "bg-warning-soft text-warning",
  delivered: "bg-success-soft text-success",
  cancelled: "bg-danger-soft text-danger",
};

/** Text label always present: status never relies on color alone. */
export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {titleCase(status)}
    </span>
  );
}

export function Pill({ children, tone = "neutral" }: { children: string; tone?: "neutral" | "danger" | "success" }) {
  const toneClass = {
    neutral: "bg-neutral-soft text-muted",
    danger: "bg-danger-soft text-danger",
    success: "bg-success-soft text-success",
  }[tone];
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${toneClass}`}>{children}</span>;
}
