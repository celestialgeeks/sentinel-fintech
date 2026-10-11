import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { toPoints, linePath, areaPath } from "@/components/dashboard/chart-helpers";
import type { StatsSummary } from "@/lib/dashboard-data";
import { formatINR } from "@/lib/dashboard-data";

/**
 * The three-up metrics grid (Zenix "spending / usage / savings"). Sentinel maps
 * those slots onto the three verdict outcomes — the money the desk actually
 * triages: Blocked (rose), On hold (amber), Cleared (emerald). Colour always
 * rides alongside a word and a figure, never hue alone (Neural Noir rule).
 * Each card keeps a small area chart at the base, exactly like the reference.
 */
const CW = 240;
const CH = 56;

interface Metric {
  key: string;
  label: string;
  value: string;
  sub: string;
  delta: number;
  accent: string; // CSS var name
  icon: "block" | "hold" | "allow";
  series: number[];
}

export function MetricsGrid({ summary }: { summary: StatsSummary }) {
  const metrics: Metric[] = [
    {
      key: "blocked",
      label: "Blocked",
      value: formatINR(summary.inr_blocked),
      sub: `${summary.verdicts.block} orders refused pre-escrow`,
      delta: 12.5,
      accent: "var(--block)",
      icon: "block",
      series: [0, 45250, 67180, 0, 22500, 9980, 0],
    },
    {
      key: "hold",
      label: "On hold",
      value: formatINR(summary.inr_on_hold),
      sub: `${summary.holds_open} awaiting you · ${summary.holds_overdue} overdue`,
      delta: -4.2,
      accent: "var(--hold)",
      icon: "hold",
      series: [7224, 7224, 0, 0, 18000, 7224, 7224],
    },
    {
      key: "cleared",
      label: "Cleared",
      value: formatINR(summary.inr_released),
      sub: `${summary.verdicts.allow} auto-released`,
      delta: 21.8,
      accent: "var(--allow)",
      icon: "allow",
      series: [69952, 41220, 88000, 52100, 90500, 61000, 148931],
    },
  ];

  return (
    <div className="grid gap-5 md:grid-cols-3">
      {metrics.map((m, i) => (
        <MetricCard key={m.key} metric={m} stagger={i + 1} />
      ))}
    </div>
  );
}

function MetricCard({ metric, stagger }: { metric: Metric; stagger: number }) {
  const points = toPoints(metric.series, CW, CH, { min: 0 });
  const line = linePath(points);
  const area = areaPath(points, CH);
  const up = metric.delta >= 0;
  const gradientId = `metric-area-${metric.key}`;

  return (
    <article
      className="liquid-glass glass-card fade-up group relative overflow-hidden rounded-2xl p-5"
      style={{ ["--stagger" as string]: stagger }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-500">
            {metric.label}
          </p>
          <p className="mt-2 font-serif text-3xl font-semibold tracking-[-0.02em] text-ink-50 tabular">
            {metric.value}
          </p>
        </div>
        <span
          className="grid size-9 shrink-0 place-items-center rounded-xl"
          style={{ background: `color-mix(in oklab, ${metric.accent} 14%, transparent)`, color: metric.accent }}
          aria-hidden
        >
          <MetricGlyph kind={metric.icon} />
        </span>
      </div>

      <p className="mt-1 text-xs text-ink-300">{metric.sub}</p>

      <div
        className={cn(
          "mt-2 inline-flex items-center gap-1 font-mono text-xs",
          up ? "text-allow" : "text-block",
        )}
      >
        {up ? <ArrowUpRight className="size-3.5" aria-hidden /> : <ArrowDownRight className="size-3.5" aria-hidden />}
        {Math.abs(metric.delta).toFixed(1)}% vs prev
      </div>

      <svg
        viewBox={`0 0 ${CW} ${CH}`}
        width="100%"
        height={CH}
        preserveAspectRatio="none"
        className="mt-4 overflow-visible"
        aria-hidden
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={metric.accent} stopOpacity="0.35" />
            <stop offset="100%" stopColor={metric.accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill={`url(#${gradientId})`} />
        <path d={line} fill="none" stroke={metric.accent} strokeWidth={2} strokeLinecap="round" />
      </svg>
    </article>
  );
}

function MetricGlyph({ kind }: { kind: Metric["icon"] }) {
  if (kind === "block")
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="8" cy="8" r="6" />
        <path d="M5 11 11 5" strokeLinecap="round" />
      </svg>
    );
  if (kind === "hold")
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="8" cy="8" r="6" />
        <path d="M6.5 6v4M9.5 6v4" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="8" cy="8" r="6" />
      <path d="M5.5 8.2 7 9.7l3.8-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default MetricsGrid;
