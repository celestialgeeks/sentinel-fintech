import { ringSegments } from "@/components/dashboard/chart-helpers";
import type { StatsSummary } from "@/lib/dashboard-data";

/**
 * Segmented verdict ring — the Zenix "AI usage ring" pattern (rounded caps, gaps
 * between arcs) applied to the verdict mix from `/portal/overview`. Hue is paired
 * with a word + count in the legend, per the Neural Noir no-color-alone rule.
 */
const R = 46;

const SEGMENTS = [
  { key: "allow", label: "Allow", color: "var(--allow)" },
  { key: "hold", label: "Hold", color: "var(--hold)" },
  { key: "block", label: "Block", color: "var(--block)" },
  { key: "degraded", label: "Degraded", color: "var(--degraded)" },
] as const;

export function VerdictRing({ mix }: { mix: StatsSummary["verdicts"] }) {
  const values = SEGMENTS.map((s) => mix[s.key]);
  const total = values.reduce((a, b) => a + b, 0) || 1;
  const segs = ringSegments(values, R, 4);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-5">
        <div className="relative size-[120px] shrink-0">
          <svg viewBox="0 0 120 120" className="size-full -rotate-90" role="img" aria-label="Verdict mix">
            <circle cx="60" cy="60" r={R} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={16} />
            {segs.map((seg, i) =>
              values[i] > 0 ? (
                <circle
                  key={SEGMENTS[i].key}
                  cx="60"
                  cy="60"
                  r={R}
                  fill="none"
                  stroke={SEGMENTS[i].color}
                  strokeWidth={16}
                  strokeLinecap="round"
                  strokeDasharray={seg.dashArray}
                  strokeDashoffset={seg.dashOffset}
                />
              ) : null,
            )}
          </svg>
          <div className="absolute inset-0 grid place-items-center">
            <div className="text-center">
              <p className="font-serif text-2xl font-semibold leading-none tabular text-ink-50">{total}</p>
              <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-ink-500">decisions</p>
            </div>
          </div>
        </div>

        <ul className="flex flex-col gap-2">
          {SEGMENTS.map((s) => (
            <li key={s.key} className="flex items-center gap-2 text-sm">
              <span className="size-2.5 rounded-full" style={{ background: s.color }} aria-hidden />
              <span className="text-ink-300">{s.label}</span>
              <span className="ml-auto font-mono tabular text-ink-50">{mix[s.key]}</span>
              <span className="w-9 text-right font-mono text-xs tabular text-ink-500">
                {Math.round((mix[s.key] / total) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default VerdictRing;
