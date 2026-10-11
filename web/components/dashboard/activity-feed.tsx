import Link from "next/link";
import { CirclePause, ShieldAlert, TriangleAlert, ArrowRight } from "lucide-react";
import type { NeedsActionRow } from "@/lib/dashboard-data";
import { formatINR, formatPct } from "@/lib/dashboard-data";

/**
 * "Recent activity" is, for this desk, the HOLD queue — `needs_action`, oldest
 * first, the decisions that are actually waiting on a human. Full-width
 * glass-strong panel, hover rows, 40px themed icon chips and right-aligned mono
 * rupee values, exactly the Zenix list anatomy pointed at real work.
 */
export function ActivityFeed({ rows }: { rows: NeedsActionRow[] }) {
  return (
    <section
      className="liquid-glass glass-strong fade-up rounded-2xl p-6"
      style={{ ["--stagger" as string]: 6 }}
    >
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg italic tracking-tight text-ink-50">Needs your action</h2>
          <p className="text-xs text-ink-500">HOLD queue · oldest first · the Binance P2P release window is 15 min</p>
        </div>
        <Link
          href="/dashboard/holds"
          className="group inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-gold transition-colors hover:text-gold-hover"
        >
          View all
          <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
        </Link>
      </div>

      <ul className="flex flex-col">
        {rows.map((row) => (
          <li key={row.order_id}>
            <Link
              href={`/dashboard/orders/${row.order_id}`}
              className="flex items-center gap-4 rounded-xl border-t border-line px-2 py-3 transition-colors duration-300 ease-[var(--ease-glass)] hover:bg-white/[0.025]"
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl" style={chipStyle(row)}>
                {row.hard_rules.length ? (
                  <TriangleAlert className="size-5" strokeWidth={1.8} aria-hidden />
                ) : (
                  <CirclePause className="size-5" strokeWidth={1.8} aria-hidden />
                )}
              </span>

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink-50">
                  {row.buyer_name}
                  <span className="ml-2 font-mono text-xs text-ink-500">{row.order_id}</span>
                </p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-ink-500">
                  <span className="uppercase tracking-wider">{row.phase.replace("_", " ")}</span>
                  <span aria-hidden>·</span>
                  <span>{row.payment_method.toUpperCase()}</span>
                  {row.hard_rules.length ? (
                    <>
                      <span aria-hidden>·</span>
                      <span className="inline-flex items-center gap-1 text-block">
                        <ShieldAlert className="size-3" aria-hidden />
                        {row.hard_rules.join(", ")}
                      </span>
                    </>
                  ) : null}
                </p>
              </div>

              <div className="shrink-0 text-right">
                <p className="font-mono text-sm tabular text-ink-50">{formatINR(row.inr_value)}</p>
                <p className="mt-0.5 font-mono text-xs tabular text-ink-500">risk {formatPct(row.risk_score)}</p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function chipStyle(row: NeedsActionRow): React.CSSProperties {
  const hard = row.hard_rules.length > 0;
  const accent = hard ? "var(--block)" : "var(--hold)";
  return {
    background: `color-mix(in oklab, ${accent} 14%, transparent)`,
    color: accent,
    border: `1px solid color-mix(in oklab, ${accent} 24%, transparent)`,
  };
}

export default ActivityFeed;
