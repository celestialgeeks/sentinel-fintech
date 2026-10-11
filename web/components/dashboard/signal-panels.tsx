import { cn } from "@/lib/utils";
import type { ProviderHealth as Provider, TopRule } from "@/lib/dashboard-data";

const STATUS = {
  ok: { color: "var(--allow)", label: "OK" },
  degraded: { color: "var(--hold)", label: "Degraded" },
  down: { color: "var(--block)", label: "Down" },
} as const;

/**
 * Signal health — `providers` from `/portal/insights`. Sentinel fails closed, so
 * a vendor being unreachable is decision-relevant, not a footnote: the dot is a
 * status word as well as a colour. Latency bars are scaled to the worst p95 in
 * the set so the reader can compare call cost at a glance.
 */
export function ProviderHealth({ providers }: { providers: Provider[] }) {
  const worst = Math.max(...providers.map((p) => p.p95_latency_ms), 1);

  return (
    <div className="flex h-full flex-col">
      <PanelTitle title="Signal health" hint="vendor fan-out · this window" />
      <ul className="mt-3 flex flex-col gap-3">
        {providers.map((p) => {
          const s = STATUS[p.status];
          return (
            <li key={p.provider} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1.5">
              <div className="flex min-w-0 items-center gap-2">
                <span className="size-2 shrink-0 rounded-full" style={{ background: s.color }} aria-hidden />
                <span className="truncate font-mono text-xs text-ink-50">{p.provider}</span>
                <span className="shrink-0 text-[10px] uppercase tracking-wider text-ink-500">{p.category}</span>
              </div>
              <span
                className="shrink-0 font-mono text-[10px] uppercase tracking-wider"
                style={{ color: s.color }}
              >
                {s.label}
              </span>

              {/* latency bar spans full width of the row */}
              <div className="col-span-2 flex items-center gap-3">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${(p.p95_latency_ms / worst) * 100}%`, background: s.color, opacity: 0.75 }}
                  />
                </div>
                <span className="w-28 shrink-0 text-right font-mono text-[10px] tabular text-ink-500">
                  {p.calls} calls · {p.p95_latency_ms}ms
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Rule leaderboard — `top_rules`. The bar is triggers; the bright cap is how many
 * of those actually led to a BLOCK, so the desk sees which rules carry teeth and
 * which just make noise.
 */
export function TopRules({ rules }: { rules: TopRule[] }) {
  const max = Math.max(...rules.map((r) => r.triggers), 1);
  const sorted = [...rules].sort((a, b) => b.triggers - a.triggers);

  return (
    <div className="flex h-full flex-col">
      <PanelTitle title="Rules firing" hint="triggers → led to block" />
      <ul className="mt-3 flex flex-col gap-3">
        {sorted.map((r) => {
          const blockRatio = r.triggers ? r.led_to_block / r.triggers : 0;
          return (
            <li key={r.name}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate font-mono text-xs text-ink-300">{r.name}</span>
                <span className="shrink-0 font-mono text-[10px] tabular text-ink-500">
                  {r.triggers}
                  {r.led_to_block > 0 ? <span className="text-block"> · {r.led_to_block} block</span> : null}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
                <div
                  className={cn("h-full rounded-full bg-gold/70")}
                  style={{ width: `${(r.triggers / max) * 100}%` }}
                >
                  <div className="h-full rounded-full bg-block" style={{ width: `${blockRatio * 100}%` }} />
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function PanelTitle({ title, hint }: { title: string; hint: string }) {
  return (
    <div>
      <h2 className="font-serif text-lg italic tracking-tight text-ink-50">{title}</h2>
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">{hint}</p>
    </div>
  );
}

export default ProviderHealth;
