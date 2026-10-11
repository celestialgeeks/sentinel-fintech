import Link from "next/link";
import { Landmark, ArrowRight } from "lucide-react";
import type { StatsSummary } from "@/lib/dashboard-data";
import { formatINR } from "@/lib/dashboard-data";

/**
 * Settlement quarantine at a glance — the rupees parked in virtual accounts
 * awaiting a sweep, plus the unmatched credits and open freeze cases that need a
 * human. Sourced from `summary.quarantine_inr / awaiting_sweep_inr /
 * unmatched_credits / lien_cases_open`. This is the "watch the money that has
 * not moved yet" tile of the bento.
 */
export function QuarantineCard({ summary }: { summary: StatsSummary }) {
  const rows = [
    { label: "In quarantine", value: formatINR(summary.quarantine_inr) },
    { label: "Awaiting sweep", value: formatINR(summary.awaiting_sweep_inr) },
    { label: "Unmatched credits", value: String(summary.unmatched_credits) },
    { label: "Open freeze cases", value: String(summary.lien_cases_open) },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-quarantine/12 text-quarantine" aria-hidden>
            <Landmark className="size-5" strokeWidth={1.8} />
          </span>
          <div>
            <h2 className="font-serif text-lg italic tracking-tight text-ink-50">Settlement quarantine</h2>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">held rupees</p>
          </div>
        </div>
      </div>

      <dl className="mt-4 flex flex-col gap-2.5">
        {rows.map((r) => (
          <div key={r.label} className="flex items-baseline justify-between border-b border-line pb-2 last:border-0">
            <dt className="text-sm text-ink-300">{r.label}</dt>
            <dd className="font-mono text-sm tabular text-ink-50">{r.value}</dd>
          </div>
        ))}
      </dl>

      <Link
        href="/dashboard/quarantine"
        className="group mt-auto inline-flex items-center gap-1 pt-3 font-mono text-[11px] uppercase tracking-wider text-gold transition-colors hover:text-gold-hover"
      >
        Open quarantine
        <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden />
      </Link>
    </div>
  );
}

export default QuarantineCard;
