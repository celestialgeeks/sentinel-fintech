import {
  DoorOpen,
  Gauge,
  Radar,
  FileStack,
  Layers,
  UserX,
  ShieldOff,
  Lock,
} from "lucide-react";

/**
 * FeaturesGrid — the 4-column glassmorphic grid from the Neural Noir spec:
 * 48px icon tiles on a gold/10 field, icon scales on hover, border brightens.
 * Titles are Inter Bold, body Inter 14px in muted ink. The eight capabilities are
 * Sentinel's real differentiators (docs/WEBSITE_CONTENT_BRIEF.md §6.4–§6.12).
 */
const FEATURES = [
  {
    icon: DoorOpen,
    title: "Two gates, before the money",
    body: "Pre-screen the buyer when the order is created, then re-check the actual credit at the release gate. Both decisions land before USDT leaves escrow.",
  },
  {
    icon: Radar,
    title: "Ten weighted signals",
    body: "Velocity, structuring, chat, wallet exposure, KYC mismatch — scored and weighted, not vibes. A clean streak ≥ 3 actively reduces behavioural risk.",
  },
  {
    icon: UserX,
    title: "Third-party payer detection",
    body: "Payer name on the bank credit ≠ Binance KYC name is the most common freeze trigger. Sentinel treats it as disqualifying at the gate — the same rule Binance applies.",
  },
  {
    icon: ShieldOff,
    title: "Fail-closed, never guesses yes",
    body: "If a required vendor is unreachable, the guard refuses to ALLOW — it returns HOLD or BLOCK, flags degraded, and names which provider failed and why.",
  },
  {
    icon: FileStack,
    title: "Evidence pack, written in advance",
    body: "Every order stores an immutable, PII-light bundle — the credit, vendor verdicts, hard rules, reasons. One click exports Markdown or JSON for your bank.",
  },
  {
    icon: Layers,
    title: "Settlement isolation",
    body: "Per-order quarantine vouchers keep suspect money out of the operating pool, so one bad credit never freezes forty good settlements.",
  },
  {
    icon: Gauge,
    title: "Fast by design",
    body: "Typical decision ~1.2s against a 6s per-order latency budget, with caching, retries and per-provider circuit breakers holding the 15-minute window.",
  },
  {
    icon: Lock,
    title: "No custody, no keys",
    body: "Advisory risk tooling. It never trades, never holds private keys, and stores last-4 of the account only. You keep the executor and the decision.",
  },
];

export function FeaturesGrid() {
  return (
    <section
      id="how-it-works"
      className="relative mx-auto max-w-7xl scroll-mt-28 px-6 py-24 md:px-12 lg:py-32"
    >
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
          How it works
        </p>
        <h2 className="mt-4 font-serif text-[clamp(2rem,5vw,3.5rem)] italic leading-tight text-ink-50">
          The danger isn&rsquo;t the crypto. It&rsquo;s the{" "}
          <span className="text-gold">credit</span>.
        </h2>
        <p className="mt-5 text-base font-light leading-relaxed text-ink-300">
          A tainted credit three hops back is what lien-marks your account.
          Sentinel is built around catching it — and documenting it — before it
          ever settles.
        </p>
      </div>

      <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => {
          const Icon = f.icon;
          return (
            <article
              key={f.title}
              className="glass group rounded-[24px] p-6 transition-all duration-300 ease-[var(--ease-noir)] hover:border-gold/40 hover:bg-glass-strong"
            >
              <span className="grid size-12 place-items-center rounded-xl bg-gold/10 text-gold transition-transform duration-300 ease-[var(--ease-noir)] group-hover:scale-110">
                <Icon className="size-6" strokeWidth={1.75} aria-hidden />
              </span>
              <h3 className="mt-5 text-xl font-bold text-ink-50">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-300">{f.body}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default FeaturesGrid;
