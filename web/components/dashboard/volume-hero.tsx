import { TrendingUp } from "lucide-react";
import { toPoints, linePath, areaPath } from "@/components/dashboard/chart-helpers";
import { formatINR } from "@/lib/dashboard-data";
import type { StatsSummary, TimeSeriesBucket } from "@/lib/dashboard-data";

/**
 * Hero balance card (Zenix "big figure + wide line chart"). For Sentinel the
 * headline number is INR cleared, not an account balance — what the desk actually
 * protects is the rupees that reached the bank without a freeze. The line plots
 * cumulative cleared volume across the window; it draws once (draw-line) and a
 * light travels the stroke forever after (shimmer-line).
 */
const W = 460;
const H = 130;

export function VolumeHero({
  summary,
  timeseries,
}: {
  summary: StatsSummary;
  timeseries: TimeSeriesBucket[];
}) {
  // Cumulative INR released across the window for a monotonically rising line.
  const perBucketReleased = timeseries.map((b) => b.allow * (summary.inr_released / Math.max(summary.verdicts.allow, 1)));
  const cumulative: number[] = [];
  perBucketReleased.reduce((acc, v) => {
    const next = acc + v;
    cumulative.push(next);
    return next;
  }, 0);

  const points = toPoints(cumulative, W, H, { min: 0 });
  const line = linePath(points);
  const area = areaPath(points, H);
  const lastPoint = points[points.length - 1];

  const stats = [
    { label: "Auto-cleared", value: `${summary.auto_cleared_pct.toFixed(1)}%` },
    { label: "Median latency", value: `${Math.round(summary.median_latency_ms)} ms` },
    { label: "Blocked", value: formatINR(summary.inr_blocked) },
    { label: "Orders", value: String(summary.orders) },
  ];

  return (
    <section
      className="liquid-glass glass-strong fade-up flex flex-col gap-8 rounded-3xl p-7 lg:flex-row lg:items-center lg:justify-between lg:p-8"
      style={{ ["--stagger" as string]: 0 }}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink-500">
            INR cleared · last 7 days
          </p>
          <span className="inline-flex items-center gap-1 rounded-full bg-allow/12 px-2 py-0.5 font-mono text-[10px] text-allow">
            <TrendingUp className="size-3" aria-hidden />
            safe
          </span>
        </div>

        <p className="mt-3 font-serif text-[2.75rem] font-semibold leading-none tracking-[-0.02em] text-ink-50 tabular sm:text-5xl">
          {formatINR(summary.inr_released)}
        </p>
        <p className="mt-3 max-w-sm text-sm leading-relaxed text-ink-300">
          Every rupee here was screened at both gates before it touched your
          account. Nothing on this line needed an evidence pack to unfreeze.
        </p>

        <dl className="mt-7 grid grid-cols-2 gap-x-6 gap-y-4 border-t border-line pt-5 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label}>
              <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">
                {s.label}
              </dt>
              <dd className="mt-1 font-mono text-lg font-semibold tabular text-ink-50">
                {s.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Chart */}
      <div className="w-full shrink-0 lg:w-[460px]">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          height={H}
          preserveAspectRatio="none"
          role="img"
          aria-label="Cumulative cleared volume over the window"
          className="overflow-visible"
        >
          <defs>
            <linearGradient id="hero-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--gold)" stopOpacity="0.28" />
              <stop offset="100%" stopColor="var(--gold)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={area} fill="url(#hero-area)" />
          <path
            d={line}
            fill="none"
            stroke="var(--gold-light)"
            strokeWidth={2}
            strokeLinecap="round"
            className="draw-line"
            style={{ ["--line-length" as string]: 1400 }}
          />
          <path
            d={line}
            fill="none"
            stroke="var(--gold-hover)"
            strokeWidth={2}
            strokeLinecap="round"
            className="shimmer-line"
            opacity={0.7}
          />
          {lastPoint ? (
            <circle cx={lastPoint.x} cy={lastPoint.y} r={4} fill="var(--gold-hover)" />
          ) : null}
        </svg>
      </div>
    </section>
  );
}

export default VolumeHero;
