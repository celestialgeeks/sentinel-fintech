import { Download, FileText } from "lucide-react";

/**
 * Evidence — the "pack you hand the bank" section (docs/WEBSITE_CONTENT_BRIEF.md
 * §6.10), the second emotional peak. Rendered as a real document at its true
 * structure so it reads as a legal artefact, not a dashboard. Compliance line —
 * last-4 only — is kept verbatim.
 */
const PACK = {
  ref: "EV-4B1C9A7D02F1",
  order: "ord_9f3c71 · 5,000 USDT → ₹4,52,250",
  verdict: "BLOCK",
  credit: {
    method: "IMPS",
    utr: "429177651234",
    vpa: "buyer@oksbi",
    account: "acct ****1234",
    payer: "Sunil Verma",
    kyc: "Ramesh Kumar (Binance)",
    confirmed: true,
  },
  vendors: [
    { name: "Chainalysis", risk: 0.98, cost: "$0.12", latency: "410 ms" },
    { name: "IDfy", risk: 0.98, cost: "$0.09", latency: "260 ms" },
    { name: "Signzy", risk: 0.91, cost: "$0.11", latency: "300 ms" },
  ],
  reasons: [
    "third_party_payer — payer name ≠ Binance KYC name",
    "mule_account — vendor risk ≥ 0.9 (hard rule)",
    "structuring — ₹1.35L across 3 credits in 40 min",
  ],
};

export function Evidence() {
  return (
    <section
      id="evidence"
      className="relative mx-auto max-w-7xl scroll-mt-28 px-6 py-24 md:px-12 lg:py-32"
    >
      <div className="grid items-center gap-14 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
            Evidence pack
          </p>
          <h2 className="mt-4 font-serif text-[clamp(2rem,5vw,3.25rem)] italic leading-tight text-ink-50">
            The pack you hand the bank, written <span className="text-gold">before</span> you need it.
          </h2>
          <p className="mt-5 text-base font-light leading-relaxed text-ink-300">
            Each order stores an immutable, PII-light bundle — the credit, every
            vendor verdict with risk / cost / latency, the decision with its hard
            rules and reasons, and timestamps. This is the proof of due diligence,
            and of being a downstream victim, that lifts a lien.
          </p>
          <ul className="mt-6 space-y-2 text-sm text-ink-300">
            <li className="flex gap-2">
              <FileText className="mt-0.5 size-4 shrink-0 text-gold" aria-hidden />
              Export as Markdown or JSON in one click — PDF on the roadmap.
            </li>
            <li className="flex gap-2">
              <FileText className="mt-0.5 size-4 shrink-0 text-gold" aria-hidden />
              Full account numbers are never stored — last 4 only.
            </li>
          </ul>
          <a
            href="#connect"
            className="mt-8 inline-flex items-center gap-2 rounded-full border border-line-strong px-6 py-3 text-sm font-medium text-ink-50 transition-colors duration-300 ease-[var(--ease-noir)] hover:border-gold hover:text-gold-hover"
          >
            <Download className="size-4 text-gold" aria-hidden />
            Download for my bank
          </a>
        </div>

        {/* Rendered document */}
        <div className="glass glow-noir rounded-[24px] p-6 md:p-8">
          <div className="flex items-center justify-between border-b border-line pb-4">
            <p className="font-serif text-lg italic text-ink-50">Evidence Pack</p>
            <p className="font-mono-ids text-xs text-gold">{PACK.ref}</p>
          </div>

          <Field label="Order" value={PACK.order} />
          <div className="flex items-baseline justify-between gap-4 border-b border-line py-3">
            <span className="text-xs uppercase tracking-[0.18em] text-ink-500">Verdict</span>
            <span className="font-mono text-lg font-medium text-block">{PACK.verdict}</span>
          </div>

          <Sub label="Credit">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 font-mono-ids text-[13px]">
              <KV k="UTR" v={PACK.credit.utr} />
              <KV k="Method" v={PACK.credit.method} />
              <KV k="Account" v={PACK.credit.account} />
              <KV k="VPA" v={PACK.credit.vpa} />
              <KV k="Payer" v={PACK.credit.payer} danger />
              <KV k="KYC" v={PACK.credit.kyc} />
            </dl>
          </Sub>

          <Sub label="Vendor verdicts">
            <ul className="space-y-1.5 text-[13px]">
              {PACK.vendors.map((v) => (
                <li key={v.name} className="flex items-center justify-between font-mono-ids">
                  <span className="text-ink-50">{v.name}</span>
                  <span className="text-ink-300">
                    risk <span className="text-block">{v.risk}</span> · {v.cost} · {v.latency}
                  </span>
                </li>
              ))}
            </ul>
          </Sub>

          <Sub label="Reasons">
            <ul className="space-y-1.5 text-[13px] text-ink-300">
              {PACK.reasons.map((r) => (
                <li key={r} className="flex gap-2">
                  <span className="text-block">•</span>
                  {r}
                </li>
              ))}
            </ul>
          </Sub>
        </div>
      </div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line py-3">
      <span className="text-xs uppercase tracking-[0.18em] text-ink-500">{label}</span>
      <span className="font-mono-ids text-[13px] text-ink-50">{value}</span>
    </div>
  );
}

function Sub({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-line py-4 last:border-b-0">
      <p className="mb-2.5 text-xs uppercase tracking-[0.18em] text-ink-500">{label}</p>
      {children}
    </div>
  );
}

function KV({ k, v, danger }: { k: string; v: string; danger?: boolean }) {
  return (
    <>
      <dt className="text-ink-500">{k}</dt>
      <dd className={danger ? "text-block" : "text-ink-50"}>{v}</dd>
    </>
  );
}

export default Evidence;
