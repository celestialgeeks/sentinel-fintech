"use client";

import { ArrowRight, AtSign, Globe, Rss } from "lucide-react";

/**
 * NeuralFooter — the multi-column footer from the Neural Noir spec: a brand
 * column with social icons in circular bordered containers, four link columns,
 * and a "Join Digest" low-opacity input with a circular arrow-submit on the far
 * right. Below it sits the always-present compliance disclaimer (docs/WEBSITE_CONTENT_BRIEF.md
 * §6.17) — the one piece of this section that is not styling.
 */
const COLUMNS = [
  {
    title: "Product",
    links: ["How it works", "Integrations", "Evidence", "Pricing", "Status"],
  },
  {
    title: "Build",
    links: ["Docs", "API reference", "SDKs", "Changelog", "Sandbox keys"],
  },
  {
    title: "Company",
    links: ["About", "Security", "Contact"],
  },
  {
    title: "Legal",
    links: ["Privacy", "Terms", "Fair-processing / DPDP notice", "Disclaimer"],
  },
];

export function NeuralFooter() {
  return (
    <>
      {/* Final CTA band */}
      <section
        id="connect"
        className="relative mx-auto max-w-7xl scroll-mt-28 px-6 pb-8 pt-24 md:px-12"
      >
        <div className="glass glow-noir mx-auto max-w-4xl rounded-[48px] px-8 py-16 text-center md:py-20">
          <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
            Get started
          </p>
          <h2 className="mt-4 font-serif text-[clamp(2rem,5vw,3.75rem)] italic leading-tight text-ink-50">
            Your next order is <span className="text-gold">already on its way</span>.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-base font-light text-ink-300">
            Create a key, POST one body, and get a verdict you can defend.
          </p>
          <a
            href="#connect"
            className="group mt-8 inline-flex items-center gap-2 rounded-full bg-white px-8 py-4 text-sm font-semibold text-black transition-all duration-300 ease-[var(--ease-noir)] hover:scale-[1.03] hover:bg-gold-hover"
          >
            Connect your bot
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </a>
        </div>
      </section>

      <footer className="relative mt-16 border-t border-line">
        <div className="mx-auto max-w-7xl px-6 py-16 md:px-12">
          <div className="grid grid-cols-2 gap-10 md:grid-cols-3 lg:grid-cols-6">
            {/* Brand column */}
            <div className="col-span-2">
              <p className="font-serif text-2xl font-bold italic text-ink-50">
                Sentinel<span className="text-gold">.</span>
              </p>
              <p className="mt-4 max-w-xs text-sm font-light leading-relaxed text-ink-500">
                Pre-settlement AML guard for Binance P2P merchants. Screen the
                buyer, isolate the credit, keep the pack.
              </p>
              <div className="mt-6 flex gap-3">
                {[AtSign, Globe, Rss].map((Icon, i) => (
                  <a
                    key={i}
                    href="#"
                    aria-label="Social link"
                    className="grid size-9 place-items-center rounded-full border border-line text-ink-300 transition-colors duration-300 ease-[var(--ease-noir)] hover:border-gold hover:text-gold-hover"
                  >
                    <Icon className="size-4" aria-hidden />
                  </a>
                ))}
              </div>
            </div>

            {/* Link columns */}
            {COLUMNS.map((col) => (
              <div key={col.title}>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ink-50">
                  {col.title}
                </p>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l}>
                      <a
                        href="#"
                        className="text-sm text-ink-500 transition-colors hover:text-gold-light"
                      >
                        {l}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            {/* Digest column */}
            <div className="col-span-2 md:col-span-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ink-50">
                Join Digest
              </p>
              <p className="mt-4 text-sm text-ink-500">
                Freeze patterns and enforcement news. No spam.
              </p>
              <form
                className="mt-4 flex items-center gap-2 rounded-full border border-line bg-white/[0.02] py-1.5 pl-4 pr-1.5"
                onSubmit={(e) => e.preventDefault()}
              >
                <input
                  type="email"
                  placeholder="you@desk.com"
                  aria-label="Email for the Sentinel digest"
                  className="min-w-0 flex-1 bg-transparent text-sm text-ink-50 placeholder:text-ink-500 focus:outline-none"
                />
                <button
                  type="submit"
                  aria-label="Subscribe"
                  className="grid size-9 shrink-0 place-items-center rounded-full bg-gold text-black transition-colors duration-300 ease-[var(--ease-noir)] hover:bg-gold-hover"
                >
                  <ArrowRight className="size-4" aria-hidden />
                </button>
              </form>
            </div>
          </div>

          {/* Disclaimer */}
          <p className="mt-14 max-w-4xl text-xs leading-relaxed text-ink-500">
            Sentinel provides risk information and evidence tooling. It is not
            legal, tax, or compliance advice, and does not file regulatory
            reports. Verify obligations with a qualified adviser. Vendor names are
            trademarks of their owners and indicate API integration only.
          </p>
          <p className="mt-3 text-xs text-ink-500">
            © {new Date().getFullYear()} Sentinel. Illustrative personas and
            sample verdicts are not customer statements.
          </p>
        </div>
      </footer>
    </>
  );
}

export default NeuralFooter;
