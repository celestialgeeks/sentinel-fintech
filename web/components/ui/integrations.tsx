"use client";

import React from "react";
import { cn } from "@/lib/utils";

/**
 * Integrations — the "plug into the bot you already run" step (docs/WEBSITE_CONTENT_BRIEF.md
 * §6.12). Three tabs (REST / Kafka / Signed requests) and the exact HMAC snippet
 * from the brief, unmodified. Glass panel on the Neural Noir canvas; the code
 * block keeps Plex Mono so ids and signatures never reflow.
 */
const TABS = [
  {
    id: "rest",
    label: "REST",
    blurb: "One POST per gate, one JSON body, one synchronous verdict.",
    body: `POST /api/v1/p2p/orders/release-gate
Authorization: Bearer <guard-key>
Content-Type: application/json

{ "order": { "id": "ord_9f3c71" },
  "phase": "release_gate",
  "payment": { "method": "imps", "utr": "429177651234",
               "payer_name": "Sunil Verma", "amount_inr": 452250,
               "confirmed": true } }

→ { "action": "reject", "verdict": "BLOCK",
    "risk": 0.93, "confidence": 0.95,
    "reasons": ["third_party_payer", "mule_account"],
    "evidence_ref": "EV-4B1C9A7D02F1" }`,
  },
  {
    id: "kafka",
    label: "Kafka",
    blurb:
      "Publish order events, consume verdicts. Idempotent on (order_id, utr) — replays are safe.",
    body: `# publish
topic: sentinel.p2p.order
{ "order_id": "ord_9f3c71", "phase": "release_gate",
  "payment": { "utr": "429177651234", "amount_inr": 452250 } }

# consume
topic: sentinel.p2p.decision
{ "order_id": "ord_9f3c71", "action": "reject",
  "verdict": "BLOCK", "step_up": [] }`,
  },
  {
    id: "signed",
    label: "Signed requests",
    blurb:
      "X-Sentinel-Timestamp + X-Sentinel-Signature = hex(hmac_sha256(secret, f\"{timestamp}.\" + body)), 300s tolerance, opt-in per key.",
    body: `import hmac, hashlib, time, httpx

ts = str(int(time.time()))
body = {"order": order, "phase": "release_gate"}
raw = json.dumps(body).encode()
sig = hmac.new(SECRET.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()

r = httpx.post(
    "https://api.sentinel.dev/api/v1/p2p/orders/release-gate",
    content=raw,
    headers={"X-Sentinel-Timestamp": ts, "X-Sentinel-Signature": sig,
             "Content-Type": "application/json"},
    timeout=8.0,
)
decision = r.json()
if decision["action"] == "release":
    release_usdt(decision["order_id"])      # ALLOW
elif decision["action"] == "hold":
    ask_buyer_for_statement(decision["step_up"])
else:
    reject_order(decision["order_id"])      # BLOCK`,
  },
];

const BULLETS = [
  "~1.2 s typical",
  "no trade logic changes",
  "sandbox with mock providers",
  "Python + Node SDK",
  "OpenAPI at /docs",
  "retry-safe",
];

export function Integrations() {
  const [active, setActive] = React.useState(TABS[2]);

  return (
    <section
      id="integrations"
      className="relative mx-auto max-w-7xl scroll-mt-28 px-6 py-24 md:px-12 lg:py-32"
    >
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-[11px] font-medium uppercase tracking-[0.3em] text-gold-light">
          Integrations
        </p>
        <h2 className="mt-4 font-serif text-[clamp(2rem,5vw,3.5rem)] italic leading-tight text-ink-50">
          Plug into the bot you <span className="text-gold">already run</span>.
        </h2>
        <p className="mt-5 text-base font-light leading-relaxed text-ink-300">
          Create a key, POST one body, and get a verdict you can defend. Your
          executor decides whether to obey — nothing here changes your strategy.
        </p>
      </div>

      {/* Tabs */}
      <div className="mt-12 flex justify-center">
        <div className="glass inline-flex rounded-full p-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActive(t)}
              className={cn(
                "rounded-full px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition-all duration-300 ease-[var(--ease-noir)]",
                active.id === t.id
                  ? "bg-white text-black"
                  : "text-ink-300 hover:text-gold-hover",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Panel */}
      <div className="glass glow-noir mx-auto mt-8 max-w-4xl overflow-hidden rounded-[24px]">
        <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-3">
          <p className="max-w-xl text-sm text-ink-300">{active.blurb}</p>
          <span className="hidden shrink-0 font-mono text-[11px] uppercase tracking-[0.2em] text-gold sm:block">
            {active.label}
          </span>
        </div>
        <pre className="overflow-x-auto px-5 py-5 text-[12.5px] leading-relaxed">
          <code className="font-mono-ids text-ink-50">{active.body}</code>
        </pre>
      </div>

      {/* Bullets */}
      <ul className="mt-8 flex flex-wrap items-center justify-center gap-3">
        {BULLETS.map((b) => (
          <li
            key={b}
            className="rounded-full border border-line bg-glass px-4 py-1.5 text-xs font-medium text-ink-300"
          >
            {b}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default Integrations;
