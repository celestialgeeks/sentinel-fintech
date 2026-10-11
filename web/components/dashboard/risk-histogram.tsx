import type { RiskBucket } from "@/lib/dashboard-data";

/**
 * Risk-score distribution. The engine's fusion thresholds are HOLD at 0.50 and
 * BLOCK at 0.80 (src/p2p/fusion.py), so each bar is tinted by the band its bucket
 * falls in and the two thresholds are drawn as hairlines. This is the score
 * build-up the Order Detail page explains, seen as a population.
 */
const W = 320;
const H = 132;
const PAD = 8;

function bandColor(low: number): string {
  if (low >= 0.8) return "var(--block)";
  if (low >= 0.5) return "var(--hold)";
  return "var(--allow)";
}

export function RiskHistogram({ buckets }: { buckets: RiskBucket[] }) {
  const max = Math.max(...buckets.map((b) => b.count), 1);
  const gap = 4;
  const barW = (W - PAD * 2 - gap * (buckets.length - 1)) / buckets.length;
  const plotH = H - 18;

  const thresholdX = (t: number) => PAD + t * (W - PAD * 2);

  return (
    <div className="flex h-full flex-col">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Risk score distribution" className="overflow-visible">
        {/* threshold hairlines */}
        {[
          { t: 0.5, label: "HOLD", color: "var(--hold)" },
          { t: 0.8, label: "BLOCK", color: "var(--block)" },
        ].map((th) => (
          <g key={th.label}>
            <line x1={thresholdX(th.t)} x2={thresholdX(th.t)} y1={4} y2={plotH} stroke={th.color} strokeWidth={1} strokeDasharray="2 3" opacity={0.5} />
            <text x={thresholdX(th.t) + 3} y={11} fill={th.color} fontSize="8" fontFamily="var(--font-mono)">
              {th.label}
            </text>
          </g>
        ))}

        {buckets.map((b, i) => {
          const h = (b.count / max) * (plotH - 10);
          const x = PAD + i * (barW + gap);
          const y = plotH - h;
          return (
            <rect
              key={i}
              x={x}
              y={y}
              width={barW}
              height={Math.max(h, b.count > 0 ? 2 : 0)}
              rx={2}
              fill={bandColor(b.low)}
              opacity={0.85}
            >
              <title>{`${b.low.toFixed(1)}–${b.high.toFixed(1)} · ${b.count}`}</title>
            </rect>
          );
        })}

        {/* baseline + x labels */}
        <line x1={PAD} x2={W - PAD} y1={plotH} y2={plotH} stroke="rgba(255,255,255,0.12)" strokeWidth={1} />
        <text x={PAD} y={H - 4} fill="var(--ink-500)" fontSize="8" fontFamily="var(--font-mono)">0.0</text>
        <text x={W - PAD} y={H - 4} fill="var(--ink-500)" fontSize="8" fontFamily="var(--font-mono)" textAnchor="end">1.0</text>
        <text x={W / 2} y={H - 4} fill="var(--ink-500)" fontSize="8" fontFamily="var(--font-mono)" textAnchor="middle">risk score</text>
      </svg>
    </div>
  );
}

export default RiskHistogram;
