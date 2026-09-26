import { Store, Users, Terminal } from "lucide-react";

/**
 * Audience — the template's editorial "team" cards (two-column, large Serif
 * names, ultra-thin wide-tracked uppercase roles in gold, grayscale→colour on
 * hover), repurposed for Sentinel's real §6.14 "who it's for" personas. There
 * are no real people to photograph and the brief forbids fabricated faces, so
 * each card's visual is a generated gold data-mesh, not a stock portrait — same
 * hover treatment, honest content.
 */
const AUDIENCE = [
  {
    icon: Store,
    name: "The Solo Desk",
    role: "1–3 accounts · < ₹50L / month",
    pain: "One tainted credit and the whole account stops moving — no team to argue with the bank.",
    first: "Opens the Live feed and the HOLD worklist first.",
    cta: "Start in sandbox",
  },
  {
    icon: Users,
    name: "The Managed Floor",
    role: "Staff + shift roster · ₹50L–5Cr / month",
    pain: "Handoffs between shifts lose the 15-minute release window and bury the evidence trail.",
    first: "Opens Orders analytics and the lien-case workspace.",
    cta: "Talk to us",
  },
  {
    icon: Terminal,
    name: "The Builder",
    role: "Bots & wallet tools · screening as a dependency",
    pain: "Wants a defensible verdict in the pipeline without taking custody or touching strategy.",
    first: "Opens the API reference and drops the release-gate POST into the bot.",
    cta: "Partner enquiry",
  },
  {
    icon: Store,
    name: "The CA-Managed Book",
    role: "Accountant-backed merchants · audit-first",
    pain: "Needs the pack to exist before the notice arrives, not reconstructed after a lien.",
    first: "Opens Evidence exports and STR-context capture per order.",
    cta: "Talk to us",
  },
];

export function Audience() {
  return (
    <section className="relative mx-auto max-w-7xl scroll-mt-28 px-6 py-24 md:px-12 lg:py-32">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
          Who it&rsquo;s for
        </p>
        <h2 className="mt-4 font-serif text-[clamp(2rem,5vw,3.5rem)] italic leading-tight text-ink-50">
          Built for the people who <span className="text-gold">hold the bag</span>.
        </h2>
      </div>

      <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-2">
        {AUDIENCE.map((a) => {
          const Icon = a.icon;
          return (
            <article
              key={a.name}
              className="glass group overflow-hidden rounded-[24px] transition-all duration-300 ease-[var(--ease-noir)] hover:border-gold/40 hover:shadow-[0_0_60px_rgba(167,139,113,0.22)]"
            >
              {/* Generated gold mesh tile — grayscale by default, colour on hover. */}
              <div className="relative aspect-[4/5] w-full overflow-hidden sm:aspect-[16/10]">
                <div className="bg-dots absolute inset-0 saturate-0 opacity-70 grayscale transition-all duration-700 ease-[var(--ease-noir)] group-hover:saturate-100 group-hover:grayscale-0" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(167,139,113,0.35),transparent_60%)] transition-opacity duration-700 group-hover:opacity-100" />
                <span className="absolute left-5 top-5 grid size-12 place-items-center rounded-xl border border-line bg-black/30 text-gold backdrop-blur-md">
                  <Icon className="size-6" strokeWidth={1.75} aria-hidden />
                </span>
                <p className="absolute bottom-4 left-5 text-[10px] font-medium uppercase tracking-[0.24em] text-ink-300">
                  Illustrative persona
                </p>
              </div>

              <div className="p-6">
                <h3 className="font-serif text-3xl italic leading-none text-ink-50">
                  {a.name}
                </h3>
                <p className="mt-2 text-[11px] font-light uppercase tracking-[0.28em] text-gold">
                  {a.role}
                </p>
                <p className="mt-4 text-sm leading-relaxed text-ink-300">{a.pain}</p>
                <p className="mt-3 text-sm text-ink-500">{a.first}</p>
                <a
                  href="#connect"
                  className="mt-5 inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-light transition-colors hover:text-gold-hover"
                >
                  {a.cta} →
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default Audience;
