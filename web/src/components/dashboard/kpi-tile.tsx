import Link from "next/link";

import { formatPercent } from "@/lib/format";

interface KpiTileProps {
  label: string;
  value: string;
  /** Relative change vs the previous period; null when there's no baseline. */
  delta?: number | null;
  /** Whether an increase is good (revenue) or bad (cancellation rate). */
  higherIsBetter?: boolean;
  comparedTo?: string;
  href?: string;
}

function Delta({ delta, higherIsBetter, comparedTo }: { delta: number | null; higherIsBetter: boolean; comparedTo: string }) {
  if (delta === null) return <p className="mt-2 text-xs text-muted">No data for the previous period</p>;
  const flat = Math.abs(delta) < 0.0005;
  const good = flat ? null : delta > 0 === higherIsBetter;
  const tone = good === null ? "text-muted" : good ? "text-success" : "text-danger";
  const arrow = flat ? "→" : delta > 0 ? "↑" : "↓";
  const sign = delta > 0 && !flat ? "+" : "";
  return (
    <p className="mt-2 text-xs text-muted">
      {/* Arrow and sign carry the direction, so it doesn't rely on color. */}
      <span className={`font-medium ${tone}`}>
        <span aria-hidden="true">{arrow} </span>
        {sign}
        {formatPercent(delta)}
      </span>{" "}
      vs {comparedTo}
    </p>
  );
}

export function KpiTile({ label, value, delta, higherIsBetter = true, comparedTo = "previous period", href }: KpiTileProps) {
  const body = (
    <>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold tracking-tight break-words sm:text-2xl">{value}</p>
      {delta !== undefined && <Delta delta={delta} higherIsBetter={higherIsBetter} comparedTo={comparedTo} />}
    </>
  );
  const box = "block rounded-lg border border-line bg-surface p-4";
  return href ? (
    <Link href={href} className={`${box} hover:border-line-strong`}>
      {body}
      <span className="mt-2 block text-xs text-accent underline-offset-2">View →</span>
    </Link>
  ) : (
    <div className={box}>{body}</div>
  );
}
