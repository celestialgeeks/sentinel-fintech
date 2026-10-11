"use client";

import React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Pricing — the three-tier layout from the Neural Noir spec (centre card
 * highlighted with a gold border + "Most Popular" badge, 48px prices, a
 * pill-shaped monthly/annual switch with a white active state). The tiers and
 * prices are Sentinel's real §6.15 structure; annual is the same plans billed
 * yearly at ~2 months free — a mockup assumption, not an invented feature.
 */
type Tier = {
  name: string;
  monthly: number | null;
  perOrder: string | null;
  blurb: string;
  features: string[];
  cta: string;
  popular?: boolean;
  custom?: boolean;
};

const TIERS: Tier[] = [
  {
    name: "Sandbox",
    monthly: 0,
    perOrder: null,
    blurb: "Everything to build against, before money or contracts.",
    features: [
      "500 orders / mo",
      "Mock vendors only",
      "7-day history",
      "No evidence export",
    ],
    cta: "Start in sandbox",
  },
  {
    name: "Desk",
    monthly: 9999,
    perOrder: "₹1.50 / screened order",
    blurb: "One live desk that wants defensible verdicts and packs.",
    features: [
      "Live vendors",
      "1 merchant + 3 seats",
      "12-month history",
      "Evidence exports",
      "HOLD worklist",
      "Quarantine vouchers",
    ],
    cta: "Connect your bot",
    popular: true,
  },
  {
    name: "Book",
    monthly: 34999,
    perOrder: "₹1.10 / screened order",
    blurb: "Scales with volume, staff shifts and policy control.",
    features: [
      "5 merchants, unlimited seats",
      "Policy tuning",
      "Vendor spend caps & routing",
      "Kafka path",
      "Lien-case workspace",
      "Priority support",
    ],
    cta: "Talk to us",
  },
];

const NOTES = [
  "Vendor pass-through at cost is shown per call in the portal; you can cap daily spend in Settings.",
  "Tiered execution: bigger tickets call pricier sources — you see which ran and what it cost.",
  "No % on your volume, ever.",
];

const INR = (n: number) => `₹${n.toLocaleString("en-IN")}`;

export function Pricing() {
  const [annual, setAnnual] = React.useState(false);

  const price = (t: Tier) => {
    if (t.monthly === null) return "Talk";
    if (t.monthly === 0) return "Free";
    const m = annual ? Math.round((t.monthly * 10) / 12 / 100) * 100 : t.monthly;
    return INR(m);
  };

  return (
    <section
      id="pricing"
      className="relative mx-auto max-w-7xl scroll-mt-28 px-6 py-24 md:px-12 lg:py-32"
    >
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
          Pricing
        </p>
        <h2 className="mt-4 font-serif text-[clamp(2rem,5vw,3.5rem)] italic leading-tight text-ink-50">
          Pay for orders you <span className="text-gold">screened</span>. Not for orders you lost.
        </h2>

        {/* Toggle */}
        <div className="mt-8 flex justify-center">
          <div className="glass inline-flex items-center rounded-full p-1 text-[11px] font-semibold uppercase tracking-[0.16em]">
            <button
              type="button"
              onClick={() => setAnnual(false)}
              className={cn(
                "rounded-full px-4 py-1.5 transition-colors duration-300 ease-[var(--ease-noir)]",
                !annual ? "bg-white text-black" : "text-ink-300 hover:text-gold-hover",
              )}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setAnnual(true)}
              className={cn(
                "rounded-full px-4 py-1.5 transition-colors duration-300 ease-[var(--ease-noir)]",
                annual ? "bg-white text-black" : "text-ink-300 hover:text-gold-hover",
              )}
            >
              Annual
            </button>
          </div>
        </div>
      </div>

      <div className="mt-14 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {TIERS.map((t) => (
          <article
            key={t.name}
            className={cn(
              "glass relative flex flex-col rounded-[24px] p-7 transition-all duration-300 ease-[var(--ease-noir)]",
              t.popular
                ? "border-gold/40 shadow-[0_0_100px_rgba(167,139,113,0.18)] lg:-translate-y-3"
                : "hover:border-gold/25",
            )}
          >
            {t.popular ? (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gold px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-black">
                Most popular
              </span>
            ) : null}

            <h3 className="font-serif text-2xl italic text-ink-50">{t.name}</h3>
            <p className="mt-2 text-sm text-ink-300">{t.blurb}</p>

            <div className="mt-6 flex items-end gap-1.5">
              <span className="text-5xl font-bold leading-none tabular text-ink-50">
                {price(t)}
              </span>
              {t.monthly ? (
                <span className="pb-1 text-sm text-ink-500">/mo</span>
              ) : null}
            </div>
            <p className="mt-1.5 font-mono-ids text-xs text-gold-light">
              {t.perOrder ?? (annual && t.monthly ? "billed yearly · ~2 months free" : "")}
            </p>

            <ul className="mt-6 space-y-2.5 text-sm text-ink-300">
              {t.features.map((f) => (
                <li key={f} className="flex gap-2.5">
                  <Check className="mt-0.5 size-4 shrink-0 text-gold" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>

            <a
              href="#connect"
              className={cn(
                "mt-8 inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-semibold transition-all duration-300 ease-[var(--ease-noir)]",
                t.popular
                  ? "bg-white text-black hover:bg-gold-hover"
                  : "border border-line-strong text-ink-50 hover:border-gold hover:text-gold-hover",
              )}
            >
              {t.cta}
            </a>
          </article>
        ))}
      </div>

      {/* Enterprise strip */}
      <div className="glass mx-auto mt-6 flex max-w-4xl flex-col items-center justify-between gap-3 rounded-[24px] px-7 py-5 sm:flex-row">
        <div>
          <p className="text-base font-semibold text-ink-50">Enterprise / API partner</p>
          <p className="text-sm text-ink-300">
            Per-order tiers, white-label, on-prem / VPC, custom vendor routing.
          </p>
        </div>
        <a
          href="#connect"
          className="shrink-0 rounded-full border border-line-strong px-5 py-2.5 text-sm font-medium text-ink-50 transition-colors hover:border-gold hover:text-gold-hover"
        >
          Partner enquiry
        </a>
      </div>

      {/* Notes + reassurance */}
      <div className="mx-auto mt-10 max-w-4xl space-y-2 text-center">
        {NOTES.map((n) => (
          <p key={n} className="text-xs text-ink-500">
            {n}
          </p>
        ))}
        <ul className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[11px] font-medium uppercase tracking-[0.16em] text-ink-300">
          <li>No custody</li>
          <li>No trading keys</li>
          <li>Last-4 account storage only</li>
        </ul>
      </div>
    </section>
  );
}

export default Pricing;
