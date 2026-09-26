"use client";

import React from "react";
import Image from "next/image";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { LivePill } from "@/components/ui/live-pill";

/**
 * NeuralHero — the interactive hero from the Neural Noir spec, now told through
 * product imagery instead of text: the central node is a screenshot of the buyer
 * initiating the transfer, and the satellites are the four moments of Sentinel's
 * workflow (screening → how we found it → where he was listed → the evidence
 * pack), wired to the centre with SVG "pulsing-branch" curves. Satellites sit
 * grayscale and bloom to colour on hover, exactly like the template's media cards.
 *
 * The images are rendered from the real Neural Noir UI (see web/public/hero) so
 * every number — the ₹4,52,250 ticket, UTR, payer≠KYC mismatch, 0.98 exposure —
 * is Sentinel's own verdict payload (docs/WEBSITE_CONTENT_BRIEF.md §6.2, §6.6).
 */

const CLUSTER_W = 1200;
const CLUSTER_H = 760;
const CENTER = { x: 600, y: 380 };

type Satellite = {
  img: string;
  tag: string;
  caption: string;
  x: number;
  y: number;
};

const SATELLITES: Satellite[] = [
  {
    img: "/hero/screening.png",
    tag: "Gate 1 · Pre-screen",
    caption: "Screening the buyer against 6 sources",
    x: 205,
    y: 178,
  },
  {
    img: "/hero/wallet.png",
    tag: "Fusion · How we found it",
    caption: "Taint traced 3 hops to a mule wallet",
    x: 998,
    y: 176,
  },
  {
    img: "/hero/watchlist.png",
    tag: "Where he was listed",
    caption: "Matched on sanctions + mule DBs · 0.98",
    x: 203,
    y: 596,
  },
  {
    img: "/hero/evidence.png",
    tag: "Gate 2 · Release-gate",
    caption: "The BLOCK pack you hand the bank",
    x: 1000,
    y: 598,
  },
];

const PROVIDERS = [
  "Chainalysis",
  "Elliptic",
  "CryptoAuthet",
  "IDfy",
  "Signzy",
  "HyperVerge",
  "Account Aggregator",
];

function branchPath(to: { x: number; y: number }) {
  const mx = (CENTER.x + to.x) / 2;
  const my = (CENTER.y + to.y) / 2 - 40;
  return `M ${CENTER.x} ${CENTER.y} Q ${mx} ${my} ${to.x} ${to.y}`;
}

const pctX = (x: number) => `${((x / CLUSTER_W) * 100).toFixed(2)}%`;
const pctY = (y: number) => `${((y / CLUSTER_H) * 100).toFixed(2)}%`;

export function NeuralHero() {
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const [par, setPar] = React.useState({ x: 0, y: 0 });

  const onMove = (e: React.PointerEvent) => {
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPar({
      x: (e.clientX - r.left) / r.width - 0.5,
      y: (e.clientY - r.top) / r.height - 0.5,
    });
  };

  return (
    <section className="relative mx-auto max-w-7xl px-6 pb-16 pt-32 md:px-12 md:pt-40 lg:pb-24">
      <div className="reveal-noir flex justify-center">
        <LivePill status="Pre-settlement guard · release-gate online" />
      </div>

      <div className="reveal-noir mx-auto mt-8 max-w-4xl text-center" style={{ animationDelay: "0.1s" }}>
        <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
          Pre-settlement AML guard · Binance P2P · USDT/INR
        </p>
        <h1 className="mt-6 font-serif text-[clamp(2.5rem,8vw,6rem)] font-normal italic leading-[1.02] tracking-tight text-ink-50">
          One <span className="text-gold">dirty credit</span> can freeze your{" "}
          <span className="text-gold">whole account</span>.
        </h1>
        <p className="mx-auto mt-7 max-w-2xl text-base font-light leading-relaxed text-ink-300 md:text-lg">
          Sentinel screens the buyer before they pay, and the rupees before they
          settle. You get ALLOW, HOLD or BLOCK in seconds — with the evidence pack
          that unfreezes the account if it ever comes to that.
        </p>
      </div>

      <div className="reveal-noir mt-10 flex flex-wrap items-center justify-center gap-4" style={{ animationDelay: "0.2s" }}>
        <a
          href="#connect"
          className="group inline-flex items-center gap-2 rounded-full bg-white px-7 py-3.5 text-sm font-semibold text-black transition-all duration-300 ease-[var(--ease-noir)] hover:scale-[1.03] hover:bg-gold-hover"
        >
          Connect your bot
          <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
        </a>
        <a
          href="#decision"
          className="inline-flex items-center gap-2 rounded-full border border-line-strong px-7 py-3.5 text-sm font-medium text-ink-50 backdrop-blur-md transition-colors duration-300 ease-[var(--ease-noir)] hover:border-gold hover:text-gold-hover"
        >
          <ShieldCheck className="size-4 text-gold" aria-hidden />
          See a real decision
        </a>
      </div>

      {/* Neural cluster — image-led */}
      <div
        ref={wrapRef}
        onPointerMove={onMove}
        onPointerLeave={() => setPar({ x: 0, y: 0 })}
        className="relative mx-auto mt-16 hidden aspect-[1200/720] w-full max-w-6xl lg:block"
      >
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox={`0 0 ${CLUSTER_W} ${CLUSTER_H}`}
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="branch" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#c9b8a0" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#a78b71" stopOpacity="0.1" />
            </linearGradient>
          </defs>
          {SATELLITES.map((s) => (
            <g key={s.img}>
              <path d={branchPath(s)} className="node-line" stroke="url(#branch)" vectorEffect="non-scaling-stroke" />
              <path d={branchPath(s)} className="node-line-flow" vectorEffect="non-scaling-stroke" />
            </g>
          ))}
          <circle cx={CENTER.x} cy={CENTER.y} r="6" fill="#a78b71" />
        </svg>

        {/* Central node — the buyer's transfer screenshot */}
        <div
          className="absolute left-1/2 top-1/2 w-[42%]"
          style={{ transform: `translate(calc(-50% + ${par.x * 14}px), calc(-50% + ${par.y * 14}px))` }}
        >
          <TransactionNode />
        </div>

        {/* Satellite media cards */}
        {SATELLITES.map((s) => (
          <div
            key={s.img}
            className="absolute w-[268px]"
            style={{
              left: pctX(s.x),
              top: pctY(s.y),
              transform: `translate(-50%, -50%) translate(${par.x * 26}px, ${par.y * 26}px)`,
            }}
          >
            <SatelliteCard s={s} />
          </div>
        ))}
      </div>

      {/* Mobile fallback — the same story, stacked */}
      <div className="mt-14 space-y-4 lg:hidden">
        <TransactionNode />
        <div className="grid gap-4 sm:grid-cols-2">
          {SATELLITES.map((s) => (
            <SatelliteCard key={s.img} s={s} />
          ))}
        </div>
      </div>

      <div className="mx-auto mt-20 max-w-4xl border-t border-line pt-8 text-center">
        <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-ink-500">
          Screening data from
        </p>
        <ul className="mt-4 flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
          {PROVIDERS.map((p) => (
            <li key={p} className="text-sm text-ink-300">
              {p}
            </li>
          ))}
        </ul>
        <p className="mt-5 text-sm text-ink-500">
          Two endpoints. No custody, no keys, no trade changes. Runs in sandbox
          with deterministic mocks before you sign a single contract.
        </p>
      </div>
    </section>
  );
}

function TransactionNode() {
  return (
    <div id="decision" className="glass glow-noir scroll-mt-28 overflow-hidden rounded-[24px] p-2.5">
      <div className="relative aspect-video w-full overflow-hidden rounded-[16px]">
        <Image
          src="/hero/transaction.png"
          alt="A Binance P2P buyer initiating an IMPS transfer of ₹4,52,250 for 5,000 USDT; the payer name on the credit is flagged."
          fill
          priority
          sizes="(max-width: 1024px) 100vw, 560px"
          className="object-cover"
        />
      </div>
      <div className="flex items-center justify-between gap-3 px-3 py-2.5">
        <p className="font-mono text-[11px] tracking-[0.12em] text-ink-300">
          ord_9f3c71 · buyer initiates transfer
        </p>
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-gold">
          Sentinel is watching
        </p>
      </div>
    </div>
  );
}

function SatelliteCard({ s }: { s: Satellite }) {
  return (
    <figure className="glass group rounded-[20px] p-2 transition-all duration-500 ease-[var(--ease-noir)] hover:scale-[1.05] hover:border-gold/40 hover:shadow-[0_0_60px_rgba(167,139,113,0.3)]">
      <div className="relative aspect-[1000/620] w-full overflow-hidden rounded-[14px]">
        <Image
          src={s.img}
          alt={s.caption}
          fill
          sizes="268px"
          className="object-cover object-top grayscale transition-all duration-700 ease-[var(--ease-noir)] group-hover:grayscale-0"
        />
      </div>
      <figcaption className="px-1.5 pb-1 pt-2">
        <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-gold">
          {s.tag}
        </p>
        <p className="mt-0.5 text-[11px] leading-snug text-ink-300">{s.caption}</p>
      </figcaption>
    </figure>
  );
}

export default NeuralHero;
