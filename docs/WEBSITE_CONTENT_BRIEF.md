# Sentinel — Website Content & Working Specification

**Purpose of this document:** a complete, decision-closed content and interaction
specification for the Sentinel marketing site + merchant portal. It exists so the
screens can be generated as high-fidelity mockups (Stitch) without anyone having
to invent product facts, field names, verdict logic, or copy.

**Everything technical in here is taken from the running codebase** — `src/p2p/*`,
`src/gateway/*`, `src/vendors/*`, `src/shared/models.py` — not from imagination.
Section 14 lists the screens that need new backend endpoints before they can be
real, so mockups can still be drawn but engineering scope stays honest.

---

## 0. How to use this with Stitch

| Step | What to feed Stitch |
|---|---|
| 1 | The Design System block (§11) as `design.md` — tokens, type, color, density |
| 2 | The landing page spec (§6) — one prompt per section, or the whole page |
| 3 | Portal screens (§9) — one prompt per screen, always include the field table |
| 4 | States & edge cases (§10, §11.5) — generate empty/loading/error/degraded too |
| 5 | §15 has paste-ready prompts ordered by build priority |

Rule for mockups: **never invent numbers, rule names, or vendor names.** The
glossary (§4) and field tables (§9) contain the real ones. A mockup that shows
"Risk: 87/100" is wrong — Sentinel's engine emits `risk_score` 0–1, displayed as
`0.93` or `93%`.

---

## 1. Product facts (grounding — read before writing any copy)

**Category.** Pre-settlement AML / fraud-taint guard for Binance P2P merchants.
Sits *beside* the merchant's existing trading automation (bot/executor); it does
not trade, does not custody funds, does not hold private keys.

**The single question it answers, per order:**
> Is this buyer and this incoming INR credit clean enough to accept the payment
> and release the USDT?

**The answer** is a machine-readable verdict the bot acts on:

| Verdict | Bot action (`action` field) | Meaning |
|---|---|---|
| `ALLOW` | `release` | Clean. Release from escrow / let the buyer pay. |
| `HOLD` | `hold` | Ambiguous or degraded. Do not release yet; `step_up` list tells you how to clear it. |
| `BLOCK` | `reject` | Tainted signal or third-party payer. Reject and let the order expire. |

**Two gates wrap the order lifecycle** (`GuardPhase`):

| Gate | Endpoint | Fires when | Question |
|---|---|---|---|
| **Pre-screen** | `POST /api/v1/p2p/orders/pre-screen` | order created / buyer claims paid, **before** INR is accepted | Should we let this buyer pay at all? |
| **Release gate** | `POST /api/v1/p2p/orders/release-gate` | bank credit confirmed, **before** USDT leaves escrow | Is the confirmed credit genuine and same-person? |

Pre-screen requires no `payment`; release-gate returns **HTTP 400** if `order.payment`
is missing (the observed INR credit is mandatory). Both run the identical
pipeline (`pipeline.guard_order`) and both also work over Kafka instead of REST.

**Pipeline order (what "how it works" diagrams must show, in this sequence):**

```
bot event → vendor fan-out → durable state (velocity/trust) → P2P rules
          → fusion → evidence bundle → settlement reconciliation
          → persistence + compliance capture → decision to bot
```

**Non-negotiable product truths (these are the differentiators, all verified in code):**

1. **Third-party payment is disqualifying at the release gate.** If the payer name
   on the bank credit ≠ the buyer's Binance-verified name (`name-match risk ≥ 0.7`),
   the verdict is `BLOCK` at confidence 0.90. This mirrors Binance's own appeal
   rule and is the most common real cause of merchant freezes.
2. **Hard blocks** fire from sanctions ≥ 0.9, confirmed mule account ≥ 0.9, severe
   on-chain wallet exposure ≥ 0.9.
3. **Fail-closed.** If a *required* vendor is unreachable, Sentinel will never
   return `ALLOW` — it degrades to `HOLD` (or `BLOCK` if composite risk ≥ 0.80),
   sets `degraded: true`, and says so in `reasons`.
4. **Evidence-first.** Every decision writes an immutable `EvidenceBundle`
   (`EV-<12 hex>`), exportable as Markdown or JSON, PII-light (last-4 of account
   only). That pack is what gets a frozen account unfrozen.
5. **Settlement isolation.** Pre-screen issues a per-order quarantine voucher
   (`VCH-<10 hex>`, virtual account + dedicated VPA). A credit that lands in the
   `operating` pool instead of `quarantine`, or has no traceable UTR, raises a loud
   reconciliation alert and forces `HOLD`. Clean funds sweep after
   `SWEEP_DELAY_HOURS = 48`.
6. **It is fast by design:** per-order vendor latency budget
   `MAX_VENDOR_LATENCY_MS = 6000`, with cache, retries, per-provider circuit
   breakers, and tiered cost escalation (bigger tickets call pricier providers).
7. **It is advisory, not a filing agent.** Compliance capture records STR-context
   on a `BLOCK`, flags 194S TDS reportability above ₹50,000 (rate 0.01), and logs
   KYC retention — it explicitly does **not** compute or file taxes.

**Risk math that must be shown accurately in UI:**

```
composite = min(1.0, max(0.5 * vendor_max_risk + 0.5 * behavioural_score,
                         vendor_max_risk))
BLOCK  if composite ≥ 0.80      HOLD if 0.50 ≤ composite < 0.80
ALLOW  if composite < 0.50      hard rule  → immediate BLOCK, confidence 0.95
```

**Ten signals the engine evaluates** (`rules.py` — use these exact names in
"what we check" tables and in the order-detail rule chips):

| Rule id (keep as-is) | Weight | Fires on | Plain-language label |
|---|---|---|---|
| `sanctions_hit` | 1.0 | sanctions risk ≥ 0.7 (hard ≥ 0.9) | Name on a sanctions / PEP / adverse-media list |
| `mule_account` | 1.0 | mule risk ≥ 0.6 (hard ≥ 0.9) | Payer bank account is a suspected mule |
| `wallet_exposure` | ≤1.0 | wallet risk ≥ 0.5 (hard ≥ 0.9) | On-chain wallet touched mixer / darknet / sanctioned address |
| `third_party_payment` | 0.9 | name-match risk ≥ 0.7 | Someone other than the buyer paid |
| `freshness` | 0.4 | 0 trades or account age < 30 days | Brand-new counterparty |
| `velocity` | ≤1.0 | ≥ 5 orders in the last hour | Same buyer firing rapid orders |
| `structuring` | 0.5 | ≥ 3 credits totalling ≥ ₹50,000 in an hour | Amounts split to stay under thresholds |
| `amount_deviation` | 0.3 | ticket ≥ ₹200,000 | Unusually large for this channel |
| `deal_red_flags` | 0.5 | chat contains any of 14 known red-flag phrases | "urgent", "different account", "my friend paid", "over pay", "outside binance", "off platform", "payment done screenshot", "cash back", "refund", "send from", "brother paid", "wife paid", "whatsapp me", "extra amount" |
| `repeat_flagged` | 0.6 | buyer has ≥ 1 prior block | Repeat offender in your own history |
| *(mitigating)* | −0.2 | `clean_streak ≥ 3` | Proven-clean repeat buyer lowers behavioural risk |

**Vendors actually wired as adapters** (adapters exist for all of these; an
unkeyed one falls back to a deterministic mock so the product runs before
contracts are signed):

| Domain | Providers | Category |
|---|---|---|
| On-chain wallet exposure | Chainalysis, Elliptic, CryptoAuthet | `wallet` |
| India mule / bank / name | IDfy, Signzy, HyperVerge | `mule`, `bank`, `name` |
| Consented bank-credit verification | Account Aggregator (Setu / SAHAMATI) | `bank` |
| Sanctions / PEP | Live feed (World-Check / LSEG / Dow Jones) + always-on local watchlist | `sanctions` |

**Real data available for the portal** (tables in `src/shared/models.py`):
`p2p_orders`, `counterparties`, `vendor_calls`, `evidence_bundles`,
`settlement_vouchers`, `lien_cases`, `compliance_events`.

**Ops metrics already emitted** (Prometheus): decision mix by
`verdict/phase/degraded`, vendor latency histogram (buckets 50→6000 ms), vendor
spend USD by provider. These are the honest source of the dashboard charts.

---

## 2. Audience & personas

Primary: **the merchant** — but in P2P the merchant is almost always two people in
one room, and the site must speak to both.

**P1 — "Setup", the owner-operator (buys).**
Runs 1–3 P2P merchant accounts personally, has a Python/Node bot or uses a
commercial P2P bot tool. Fear: one ₹20,000 tainted credit freezes a ₹40 lakh
operating account mid-month, and every rupee in it is unavailable until a police
station in another state is satisfied. Buys speed + proof. Careful with API keys.
Wants: "does this plug into *my* bot without rewriting it?"

**P2 — "Risk", the ops/manager (uses).**
Watches the live feed, works the `HOLD` queue, answers the bank's emails. Doesn't
write code. Wants: one screen, obvious next action, export button that works.

**P3 — "Bank", the external audience (indirect).**
Bank compliance officer, cyber cell, or the merchant's CA. They never log in, but
they read the evidence pack. This is why export typography and one-page completeness
matter more than usual.

Secondary (keep on the site, never lead with it): compliance teams at small VDA
service providers, and P2P bot tool vendors who could embed Sentinel.

**Persona ⇒ site consequence.** The landing page leads with *freeze prevention and
evidence*, not with "AI-powered AML". The portal's home screen is *today's money
you didn't lose*, not a vanity KPI grid.

---

## 3. What the merchant actually does all day (drives IA)

1. Bot calls **pre-screen** on new order → buyer is told to pay into a voucher VPA.
2. Order sits minutes; buyer pays; bank credit appears (bot or AA feed reads it).
3. Bot calls **release-gate** with the confirmed credit + UTR.
4. Merchant sees `ALLOW` → bot releases USDT. Or `HOLD` → merchant opens the order,
   reads `step_up`, asks the buyer for a statement showing UTR + own name.
   Or `BLOCK` → bot rejects; merchant glances at reasons, moves on.
5. End of day: merchant checks INR blocked vs released, works remaining `HOLD`s,
   reviews the quarantine pool awaiting the 48 h sweep.
6. Occasionally: a lien/freeze notice arrives by email → merchant opens a case on
   the freeze screen, attaches the notice, downloads the evidence pack, replies.

**The site must mirror steps 1–6.** Steps 3–5 are the portal's core; step 6 is the
emotional payoff that sells the product and deserves a hero-adjacent section.

---

## 4. Terminology glossary (single source of truth for all UI text)

| Use exactly this | Never use | Why |
|---|---|---|
| Guard / the guard | "the model" | It is rules + vendors, not one model |
| Verdict: ALLOW / HOLD / BLOCK | approve/reject, green/red | Matches `GuardVerdict` enum, machine-paired |
| Risk score `0.93` (or `93%`) | 87/100 | Field is 0–1 float |
| Confidence `0.95` | certainty | Distinct field |
| Gate: pre-screen / release-gate | stage 1/2 | Matches `GuardPhase` |
| Tainted credit / dirty money | "fraud" | Freeze comes from the credit |
| Mule account | "stolen account" | Industry term merchants know |
| Third-party payment | name mismatch | Binance's own wording |
| Evidence pack | report | Exported, handed to bank/police |
| Quarantine voucher | escrow account | `pool = quarantine` |
| UTR | "transaction id" | India-specific traceability key |
| Freeze / lien case | "dispute" | `lien_cases` |
| Degraded | "error" | `degraded: true` has a product meaning |
| Counterparty trust · clean streak | reputation | `counterparties.clean_streak` |
| Step-up | "manual review" | `decision.step_up` |

Tone: **plain, technical, unsensational.** Short declaratives. Numbers over
adjectives. Indian-English conventions (₹ lakh/crore, 24-hour IST timestamps).
Never promise "no freezes ever" — promise "you will not be the person who
couldn't explain the credit."

---

## 5. Sitemap / information architecture

```
sentinel.dev
├── /                         Landing page (§6)
├── /how-it-works             Signals, fusion math, fail-closed (§7.1)
├── /integrations             REST + Kafka, HMAC, bot snippets (§7.2)
├── /evidence                 Evidence pack + freeze response (§7.3)
├── /pricing                  §7.4
├── /merchants                Who this is for + volume stories (§7.5)
├── /faq  /blog  /docs  /status  /legal/{privacy,terms,disclaimer}
├── /login                    §8.1      /signup  /signup/verify-email
├── /setup                    Connection wizard (never connected yet) §8.2
└── /app                      Portal (after login)
    ├── /app/overview         Today's protection          §9.1
    ├── /app/live             Live guard feed (streaming)  §9.2
    ├── /app/orders           Transaction history          §9.3
    ├── /app/orders/{id}      Order detail + evidence      §9.4
    ├── /app/holds            HOLD / step-up worklist      §9.5
    ├── /app/buyers           Counterparties & trust       §9.6
    ├── /app/settlement       Quarantine pool & vouchers   §9.7
    ├── /app/freezes          Lien cases                   §9.8
    ├── /app/compliance       STR-context, 194S, exports   §9.9
    ├── /app/insights         Vendor latency, spend, mix   §9.10
    └── /app/settings         Integration, keys, policy, team §9.11
```

Portal nav (left rail, 9 items, grouped):

```
MONITOR      Overview · Live · Orders · Holds
PEOPLE       Buyers
MONEY        Settlement
INCIDENTS    Freezes
PAPERWORK    Compliance · Insights
ACCOUNT      Settings
```

---

## 6. Landing page — section by section (copy is final, not draft)

Order matters: problem → mechanism → proof of mechanism → payoff (evidence) →
how to plug in → numbers → objections → CTA. Mobile: same order, no carousels.

### 6.1 Sticky nav
Left: Sentinel wordmark (shield/scan glyph). Center: `How it works` · `Integrations`
· `Evidence` · `Pricing` · `Docs`. Right: `Log in` (ghost) · `Connect your bot`
(solid). On scroll past hero, collapse height 72→56 px and add a hairline border.
`Live status` dot links `/status`.

### 6.2 Hero
- **Eyebrow:** `PRE-SETTLEMENT AML GUARD · BINANCE P2P · USDT/INR`
- **H1:** `One dirty credit can freeze your whole account.`
- **Sub-headline:** `Sentinel screens the buyer before they pay, and the rupees
  before they settle. You get ALLOW, HOLD or BLOCK in seconds — with the evidence
  pack that unfreezes the account if it ever comes to that.`
- **Primary CTA:** `Connect your bot` → `/signup`. Microcopy under: `Two endpoints.
  No custody, no keys, no trade changes.`
- **Secondary CTA:** `See a real decision` → anchor to §6.5 (scrolls to verdict demo).
- **Right visual (not stock art):** a live-looking **verdict card**, mid-animation
  settling from `HOLD` to `BLOCK`, showing `risk 0.93 · confidence 0.90 ·
  hard_rules: mule_account · third-party payer name "Sunil Verma" ≠ Binance KYC
  "Ramesh Kumar" · UTR 429177651234`. Merchants should recognise their own order.
- Optional ticker under the card: `Blocked today across monitored merchants:
  ₹41.2 lakh` with note `illustrative` in mockups until real aggregates exist.

### 6.3 Trust bar (logos, small, honest)
`Screening data from` → Chainalysis · Elliptic · CryptoAuthet · IDfy · Signzy ·
HyperVerge · Account Aggregator (Setu / SAHAMATI). Plus one text chip:
`Runs in sandbox with deterministic mocks before you sign a single contract.`

### 6.4 Problem section — "how a freeze actually happens"
- **H2:** `The danger isn't the crypto. It's the credit.`
- **Body:** A buyer pays ₹18,000 from an account that received cyber-fraud money
  three hops back. You release USDT because the screenshot looked right and the
  balance appeared. Weeks later a cyber cell in another state traces the victim's
  money forward, the bank lien-marks your account, and every rupee in it —
  including clean settlement money from fifty other buyers — stops moving. Under
  the PMLA / Cyber-TAT (N4C) process the freeze follows the money, not your intent.
- **Visual:** 4-step horizontal flow, `Victim → Mule → Buyer's account → YOUR
  account → LIEN`, with the last two edges in red and a Sentinel gate glyph between
  "buyer's account" and "your account" labelled `you decide here`.
- **Three stat cards (illustrative until instrumented, tag them):**
  `Manual review loses the 15-minute release window` ·
  `A single tainted credit freezes the whole account, not just the order` ·
  `Unfreezing takes evidence you can only produce in advance`.

### 6.5 The two gates (the "aha" section — highest value)
- **H2:** `Two gates. Both before the money is committed.`
- Layout: horizontal timeline of an order lifecycle with two gates inserted, then
  two cards.

```
Order created ──► [ GATE 1 · PRE-SCREEN ] ──► Buyer pays into your voucher ──►
Credit lands + UTR confirmed ──► [ GATE 2 · RELEASE-GATE ] ──► USDT leaves escrow
```

**Card A — Pre-screen.** `POST /api/v1/p2p/orders/pre-screen`. Inputs: Binance
user, KYC-verified name, trade count, completion rate, account age, chat snippet,
device/IP, wallet addresses, ticket size. Output: verdict + a quarantine voucher
(`VCH-…`) with its own virtual account and VPA, so the incoming credit is
individually UTR-traceable. Copy line: `Stop the deal before you have money in
transit, and know exactly which credit belongs to which order.`

**Card B — Release gate.** `POST /api/v1/p2p/orders/release-gate`. Requires the
observed credit (`payment` — method, payer name on account, bank, masked account,
IFSC, VPA, UTR, amount, credit timestamp, `confirmed`). Reconciles the credit
against its voucher and re-screens with bank data. Copy line: `A release gate that
only reads a screenshot is a gate that only looks polite.` Note: sending
release-gate without `payment` returns `400`, and Sentinel says why.

### 6.6 Live verdict walkthrough (the "See a real decision" anchor)
Interactive-looking tabbed block, three tabs = `ALLOW`, `HOLD`, `BLOCK`. Each shows
the actual `GuardDecision` fields a merchant sees, in this card shape:

```
BLOCK   order ord_9f3c71   release-gate      USDT 5,000 → INR 45,250
risk 0.93     confidence 0.95
Hard rule: mule_account (IDfy 0.98)   ·   Third-party payment: "Sunil Verma" ≠ "Ramesh Kumar"
Signals: velocity 6 orders/hr · structuring ₹1.35L in 3 credits · chat "my friend paid"
Spend: $0.42 across 5 calls      Latency: 1,240 ms      Evidence: EV-4B1C9A7D02F1
Bot action: reject — do not release. Order expires.
```

`HOLD` tab must show the four `step_up` items verbatim from `fusion._STEP_UP`:
1. `Ask buyer for a bank statement screenshot showing the UTR and their own name.`
2. `Re-confirm the credit via the Account Aggregator / bank feed (not the buyer screenshot).`
3. `Hold 30 minutes and re-screen once the payer bank-account data is available.`
4. `If the payer cannot prove same-person funds, reject and let the order expire.`

Copy under block: `Every field here is returned by one call, and every one of them
is stored. Nothing is a black box.`

### 6.7 What we check (signal grid)
- **H2:** `Ten signals on every order. Weighted, not vibes.`
- 3×4 grid of chips using the §1 rule table, each: label + one-line trigger +
  weight bar. Include the mitigating `clean_streak ≥ 3` chip in a different accent
  ("trust earned"), because it answers "will this block my good repeat buyers?".
- Footnote: `Vendor ≥0.9 on sanctions, confirmed mule, or severe wallet exposure is
  a hard block regardless of score.`

### 6.8 Third-party payments (own full-width section — merchants feel this)
- **H2:** `Someone else paid. That's the freeze.`
- Body: the payer on the bank credit isn't the Binance-verified buyer, so the money
  is not the trader's money. It's the most common way a merchant becomes the last
  hop of somebody else's crime, and it's the pattern Sentinel treats as
  disqualifying at the release gate — `BLOCK`, confidence 0.90 — the same rule
  Binance applies in merchant appeals.
- Side visual: two receipt illustrations, `Payer: Ramesh Kumar = Buyer ✓` vs
  `Payer: Sunil Verma ≠ Buyer ✗`.

### 6.9 Fail-closed & degraded mode (trust section)
- **H2:** `When a data source is down, Sentinel never guesses yes.`
- Body: if a required vendor is unreachable, the guard refuses to `ALLOW`. It
  returns `HOLD` (or `BLOCK` above 0.80 composite), flags `degraded: true`, and
  tells you which provider failed and why. Per-provider circuit breakers, two
  retries, a 6-second latency budget, and result caching keep the 15-minute window;
  resilience never becomes silent consent.
- Visual: small diagram `vendor timeout → degraded verdict → HOLD + named reason`,
  plus a real `reasons` string: `Required vendor unavailable - degraded, refusing
  to auto-allow`.

### 6.10 Evidence pack (the second emotional peak)
- **H2:** `The pack you hand the bank, written before you need it.`
- Body: each order stores an immutable, PII-light bundle — order & ticket, buyer
  profile snapshot, the credit (method, UTR, VPA, `acct ****1234`, payer name,
  confirmed flag), every vendor verdict with risk/detail/cost/latency/raw ref, the
  decision with hard rules and reasons, timestamps. Export Markdown or JSON, one
  click; PDF later. This is proof of due diligence and of being a downstream
  victim, which is the argument that lifts a lien.
- Visual: rendered `Evidence Pack EV-…` document at real structure (see §9.4),
  with a `Download for my bank` button. Add a line: `Full account numbers are never
  stored — last 4 only.`

### 6.11 Settlement isolation (differentiator, keep short)
- **H2:** `Contain one bad credit. Keep forty good settlements moving.`
- Body: per-order voucher → credit is traceable to one order → suspect money stays
  in the quarantine pool while the operating float keeps working → clean funds
  sweep after the 48-hour complaint window. Misrouted credits (landed in
  `operating`, or no UTR) raise an alert and force `HOLD`.

### 6.12 Integration section — "connect to your automation" (the conversion step)
- **H2:** `Plug into the bot you already run.`
- Three tabs: `REST` · `Kafka` · `Signed requests`.
  - **REST:** one POST per gate, one JSON body, one synchronous verdict.
  - **Kafka:** publish order events to `sentinel.p2p.order`; consume verdicts from
    `sentinel.p2p.decision`. Idempotent on `(order_id, utr)` — replays are safe.
  - **Signed requests:** `X-Sentinel-Timestamp` +
    `X-Sentinel-Signature = hex(hmac_sha256(secret, f"{timestamp}." + body))`,
    300-second tolerance, opt-in per key.
- Show this real snippet (do not paraphrase):

```python
import hmac, hashlib, time, httpx

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
    reject_order(decision["order_id"])      # BLOCK
```

- Feature bullets: `~1.2 s typical` · `no trade logic changes` · `sandbox with mock
  providers` · `Python + Node SDK` · `OpenAPI at /docs` · `retry-safe`.

### 6.13 Numbers / portal preview
- **H2:** `What your Monday morning looks like.`
- Product screenshot of `/app/overview` (§9.1) in a browser frame with a real
 -looking week of data. Four stat captions beside it:
  `Orders screened` · `INR blocked` · `Median decision time` · `Auto-cleared
  (never touched by a human)`.
- Add honest sub-caption: `Every card below is a portal screen, not a marketing
  chart.`

### 6.14 Who it's for
Three cards, self-serve language: `Solo merchant, 1–3 accounts, <₹50L/month` ·
`Desk with staff and a shift roster, ₹50L–5Cr/month` · `Bot & wallet tool builders
who want screening as a dependency`. Each: pain line, what they click first in the
portal, CTA text `Start in sandbox` / `Talk to us` / `Partner enquiry`.

### 6.15 Pricing
- **H2:** `Pay for orders you screened. Not for orders you lost.`
- Recommended structure (decision-closed for mockups):

| Plan | Price | Includes |
|---|---|---|
| **Sandbox** | Free | 500 orders/mo, mock vendors only, 7-day history, no evidence export |
| **Desk** | ₹9,999/mo + ₹1.50 per screened order | Live vendors, 1 merchant + 3 seats, 12-month history, evidence exports, HOLD worklist, quarantine vouchers |
| **Book** | ₹34,999/mo + ₹1.10 per screened order | 5 merchants, unlimited seats, policy tuning, vendor spend caps & routing, Kafka path, lien-case workspace, priority support |
| **Enterprise / API partner** | Talk | Per-order tiers, white-label, on-prem/VPC, custom vendor routing |

- Notes that must appear: `Vendor pass-through at cost is shown per call in the
  portal; you can cap daily spend in Settings` · `Tiered execution: bigger tickets
  call pricier sources — you see which ran and what it cost` ·
  `No % on your volume, ever`.
- Reassurance strip: `No custody` · `No trading keys` · `Last-4 account storage
  only` · `Delete my data`.

### 6.16 FAQ (objection handling — real objections)
1. **Will this make me miss the 15-minute release window?** Typical decision ~1.2 s,
   hard budget 6 s/order; a `HOLD` is faster than an unpaid lien.
2. **Does it stop my bot or take over trading?** It returns `release` / `hold` /
   `reject`. Your executor decides whether to obey. Nothing changes your strategy.
3. **What if a good repeat buyer gets `HOLD`?** Clean streak ≥ 3 actively reduces
   behavioural risk; every reason is listed, and step-up is designed to be answerable
   in a chat thread.
4. **What happens if a vendor is down?** `degraded: true`, never `ALLOW`, reason
   names the provider.
5. **Do you store my buyers' bank details?** Method, UTR, VPA, IFSC, masked last-4,
   payer name, amount, timestamp. Full account numbers are never persisted.
6. **Which exchange/asset?** Built for Binance P2P USDT↔INR; any bot that can POST
   JSON or publish to Kafka.
7. **Do you file STRs or TDS?** No. Sentinel records STR-context, flags 194S
   reportability above ₹50,000, retains KYC pointers, and exports. Your CA /
   compliance officer files.
8. **Do you guarantee no freeze?** No product does. Sentinel makes each credit
   individually traceable, evidenced, and defensible, and blocks the patterns that
   most often cause freezes.
9. **How do I remove myself?** Delete key → portal → Settings → Integration →
   Revoke. 30-day grace, then purge.

### 6.17 Footer CTA + footer
- **H2:** `Your next order is already on its way.`
- Sub: `Create a key, POST one body, and get a verdict you can defend.` ·
  CTA `Connect your bot`.
- Footer columns: `Product` (How it works, Integrations, Evidence, Pricing, Status)
  · `Build` (Docs, API reference, SDKs, Changelog, Sandbox keys) · `Company`
  (About, Security, Contact) · `Legal` (Privacy, Terms, Fair-processing / DPDP
  notice, Disclaimer).
- **Disclaimer (small, always present):** `Sentinel provides risk information and
  evidence tooling. It is not legal, tax, or compliance advice, and does not file
  regulatory reports. Verify obligations with a qualified adviser. Vendor names are
  trademarks of their owners and indicate API integration only.`

---

## 7. Marketing subpages

### 7.1 `/how-it-works`
The §1 pipeline diagram, enlarged, each stage a card: *fan-out* (categories,
caching, retries, breakers, tier, fail policy) → *state* (Redis velocity 48 h
window, 90-day trust with decay) → *rules* (the §1 table in full) → *fusion* (the
formula + threshold bands rendered as a ruler with `ALLOW <0.50 · HOLD 0.50–0.79 ·
BLOCK ≥0.80`) → *evidence* (bundle schema) → *settlement* (voucher, pools, 48 h) →
*compliance* (advisory). Ends with `Why we fail closed` and `What we never do`
(no custody, no trading, no filing, no selling counterparty data).

### 7.2 `/integrations`
Matrix of bot setups (commercial P2P bot tools, custom `python-binance` scripts,
`ccxt`, exchange-official APIs), each with the one hook point; REST contract table
for every `GuardDecision` field with type + range + meaning; Kafka topics with a
sample `sentinel.p2p.order` payload and the idempotency rule; HMAC worked example
with signature + timestamp; error contract (`400` missing payment, `401` bad
signature, `429` rate-limit with `Retry-After`); SDK tabs (Python/Node/cURL);
`/docs` (Swagger) link; postman-style copyable requests.

### 7.3 `/evidence`
Full-page sample evidence pack rendered exactly as `evidence.to_markdown` emits it
(reference, order, phase, generated, verdict/action/risk/confidence, Order, Buyer,
Payment credit, Vendor signals, Hard rules, Reasons). Two buttons:
`Download this pack (MD)` / `(JSON)`. Below: *How to use it with your bank* —
cover-email template, what to attach, the four things a lien notice asks for,
a checklist to fill a Section 91 CrPC-style reply, and `Open a freeze case` CTA
into the portal. Include the `assembled: true/false` reality: if the order was
guarded, the pack is instant; if not, Sentinel says so rather than inventing one.

### 7.4 `/pricing` — §6.15 expanded with a per-order cost calculator
Slider: `orders/day` × `avg ticket (₹)` → estimated monthly (plan + per-order +
vendor pass-through, with tiering note: pre-screen tier 0, ≥₹2L escalates to tier 2).

### 7.5 `/merchants`
Three mini case stories (clearly labelled illustrative): the 4 a.m. `BLOCK` that
saved a ₹2.4L credit; the `HOLD` cleared by one statement; the lien answered in a
day with a pack. Each ends with the exact screen that produced the outcome.

### 7.6 `/docs`, `/status`, `/blog`
Docs: quickstart, API, decision semantics, rule reference, vendor matrix,
data-retention, security model. Status: per-gate latency p95 + vendor health +
incidents. Blog: freeze anatomy, rule changelogs, mule-network patterns from
aggregate data (PII-light).

---

## 8. Login, signup, and "connect your automation"

### 8.1 Login / signup
- Fields: work email, password (min 12), or **magic-link/OTP primary** (merchants
  change phones); optional TOTP. No "Sign in with Google" as the only path —
  many merchants use shared/burner accounts. `Continue as demo merchant` for a
  read-only seeded workspace (drives landing → portal conversion).
- `Forgot password` · `Lockout notice after 5 tries` · `New device email`.
- Signup adds: business/display name, country default **India**, monthly volume
  band, "Do you run a bot?" `Yes (my own code)` / `Yes (a tool)` / `Not yet` —
  this branches the wizard.
- Consent line: `I understand Sentinel advises on risk and does not file regulatory
  reports.`

### 8.2 `/setup` — Connection wizard (the product's most important flow)
5 steps, right-side persistent `What the bot sees` preview panel that fills in as
the merchant progresses. Progress in local state + server-side `merchant` row so
they can leave and resume.

| Step | Title | Merchant does | Product shows |
|---|---|---|---|
| 1 | **Identity** | Confirm merchant id (`merchant_id` sent with every order), add Binance P2P account handle(s) | `merchant_id` is how history is partitioned; keep it stable |
| 2 | **Credentials** | Generate **Guard key**; copy `GUARD_HMAC_SECRET` once (shown one time, `Reveal`/`Copy`) | Signature header spec; `Revoke` lives in Settings |
| 3 | **Transport** | Pick `REST` or `Kafka` | REST: two URLs + snippet. Kafka: `sentinel.p2p.order` publish / `sentinel.p2p.decision` consume + bootstrap/sasl fields |
| 4 | **Test with mock data** | Click `Run sandbox pre-screen` / `Run sandbox release-gate`; or paste a real historic order | Live `GuardDecision` JSON, syntax-highlighted, with the verdict card |
| 5 | **Go live** | Toggle enforcement `Observe only` → `Enforce`; set `HOLD handling` (auto-step-up vs manual) | `Observe only` returns verdicts but never blocks your flow — the safe first 48 h |

Wizard states to design: key-created toast, signature-mismatch `401` explainer
("your timestamp drifted / body re-serialised — send the raw bytes"), payment-
missing `400` explainer, `Step 4` sandbox verdict always available even with no
vendor keys (mock fallback), and a `Skip, take me to the dashboard` escape hatch.

### 8.3 Post-login routing
`merchant_id` has no orders → `/app/overview` empty state with the wizard CTA.
Has orders → `/app/overview`. Unfinished wizard → banner `Your bot isn't connected
yet — 2 minutes left` with `Resume setup`.

---

## 9. Merchant portal — screen specifications

Global chrome: left nav (§5) collapsible to icons; top bar with merchant/account
selector (`merchant_id` switcher), global time range (`Today · 7d · 30d · Custom`),
global search (order id / UTR / buyer / VPA / voucher ref / evidence ref), live
`Connected` vs `Degraded` status pill, user menu. All tables: sticky header,
row-click → detail drawer or page, `Shift+click` multi-select for bulk export,
column visibility, 25/50/100 page size, server sort, URL-persisted filters.
Timestamps in **IST with a UTC tooltip**. Money as `₹4,52,250` (Indian grouping)
plus `5,000 USDT`.

### 9.1 `/app/overview` — Today's protection
**Job:** "am I safe, is my money moving, does anything need me right now?"

- **Row 1 — hero KPIs (5 cards, sparkline behind each):** `Orders screened` ·
  `INR blocked` (sum of `inr_value` where verdict BLOCK) · `INR released` ·
  `Auto-cleared %` (ALLOW with no human touch) · `Median decision time` (ms).
  Each card: big number, delta vs yesterday, tiny 7-day sparkline.
- **Row 2 — verdict mix:** stacked horizontal bar `ALLOW/HOLD/BLOCK` with counts +
  % (from `sentinel_p2p_guard_decisions_total`), split by phase (pre-screen vs
  release-gate) as a toggle.
- **Row 3 — needs you (action queue):** `HOLD` orders with age badges (>30 min =
  amber, >2 h = red, since the release window is 15 min), each row = order id,
  amount, top reason, `Open step-up →`. Plus `Degraded` decisions needing a
  vendor check, and quarantine credits awaiting sweep.
- **Row 4 — risk distribution:** histogram of `risk_score` (0–1 in 20 buckets)
  with threshold rules overlaid at 0.50 / 0.80; hover → count + example orders.
- **Row 5 — top exposures (this week):** table of 5 buyers by `seen/flagged`
  (`counterparties`), and 5 most-triggered rule names with counts.
- **Row 6 — money in quarantine:** pool balance, vouchers `issued` vs swept vs
  stale, `sweep_after` countdown.
- Footer strip: `Vendor spend today (USD)` and `Freeze cases open`.
- Empty state (new merchant): `Waiting for your first order` + wizard CTA +
  `Run a sandbox decision` + fake-data `Preview the dashboard` toggle clearly
  marked `sample data`.

### 9.2 `/app/live` — Live guard feed
**Job:** watch decisions land, in real time, and intervene on one.

- Full-width feed, newest first, ~8 rows visible, auto-scroll pinned with
  `Paused` control. Each row is a compact verdict capsule: `time IST`, order id,
  phase, ticket `₹`, buyer, verdict chip, risk, confidence, latency ms, degraded
  icon, hard-rule chips, `Open` link.
- Colour rules: ALLOW `#0F9D58`-family solid chip, HOLD amber, BLOCK red, DEGRADED
  purple outline + `!`.
- Filters: phase, verdict, min-risk slider (0–1), merchant, has-hard-rule only,
  degraded only.
- Side panel (right, 380 px): `Signal health` — each provider status
  (`ok / unavailable / error / skipped`), p95 latency, 24 h call count, circuit
  breaker open state, cache-hit rate. Because the honest answer to "is the guard
  working?" lives here.
- Controls: `Pause` · `Jump to newest` · `Open as JSON` (the raw decision) ·
  keyboard `↑/↓` select, `Enter` open, `B` block-note.
- Connection states: streaming dot, reconnect spinner, `Feed offline — decisions
  are still being made` fallback that switches to 15 s polling.
- Mobile: cards not rows; filters collapse; side panel becomes a tab.

### 9.3 `/app/orders` — Transaction history (the tracked/visualised ledger)
**Job:** find any order, in any state, prove what happened.

Columns (all real fields; default visible marked ★):

| Column | Field | Notes |
|---|---|---|
| ★ | `Order` | `order_id`, monospace, copy on click |
| ★ | `Decided` | `decided_at`, IST |
| ★ | `Phase` | `pre_screen` / `release_gate` chip |
| ★ | `Ticket` | `inr_value` (₹) with `qty`+`asset` (5,000 USDT) under |
| ★ | `Buyer` | `buyer_name` + `buyer_user` (muted) + country flag |
| ★ | `Verdict` | `verdict` chip + `action` tooltip |
| ★ | `Risk` | `risk_score` bar + number, 3 dp |
| ★ | `Conf.` | `confidence` |
| ★ | `Rules` | `hard_rules` chips first (red), then `reasons` count as `+3` popover |
| | `Payer` | `payer_name_on_account` + `***1234` masked + `utr` |
| | `Method` | `payment.method` (upi/imps/neft/rtgs/bank_transfer/other) |
| | `Voucher` | `voucher_ref`, `pool`, `status` |
| ★ | `Evidence` | `EV-…` link icon → opens pack |
| | `Degraded` | boolean icon |
| | `Spend` | vendor `cost_usd` total for the order |
| | `Latency` | max `vendor_calls.latency_ms` |

- Filters (left drawer, chip list shown above table): date range · verdict (multi)
  · phase · risk ≥ slider · hard rule (multi-select of the §1 names) · merchant ·
  buyer search · has UTR? · payment method · degraded · pool · compliance event
  type (`STR_CONTEXT` / `TDS_194S` / `KYC_RETENTION`).
- Saved views: `Needs action (HOLD)`, `Blocked third-party`, `High risk cleared`,
  `Degraded calls`, `Awaiting sweep`.
- Bulk: select rows → `Export CSV` · `Download evidence packs (zip)` ·
  `Add to freeze case`.
- Inline analytics header above the table: `1,284 orders · 96 BLOCK ·
  ₹18.4L blocked · median 1.18 s` (recomputed on filter change — merchants need
  to see that filters change the math).
- Row click → `/app/orders/{id}` (§9.4). Search hit highlight. Deep-linkable URLs
  (`?verdict=BLOCK&risk_min=0.8&from=2026-09-01`) so a merchant can paste a view
  into a bank email.
- States: no results (clear filters / widen date), 10 k+ rows (`refine to export`),
  partial data (orders guarded pre-onboarding greyed `not screened by Sentinel` —
  important honesty in a ledger), DB write failure on an old order
  (`verdict reached the bot; history row unavailable`, from best-effort persistence).

### 9.4 `/app/orders/{id}` — Order detail + evidence (the product's crown jewel)
**Job:** from one screen, understand the decision, defend it, act on it.

Layout: header band + 3 tabs + right rail (sticky).

**Header band:** `ord_9f3c71` · `release-gate` · verdict chip `BLOCK` ·
`reject` · `₹4,52,250 (5,000 USDT @ ₹90.45)` · buyer `Ramesh Kumar (@u_amesh, IN)`
· `Decided 04:12:33 IST · risk 0.93 · confidence 0.95 · 1,240 ms · $0.42` ·
actions `Download evidence` · `Copy decision JSON` · `Open freeze case` ·
`Override & release` (secondary, red-outline, **requires typed reason + audit
entry**).

**Tab 1 — Why (`decision`).** Verdict + action + `step_up` checklist (clickable
`Mark done`, which timestamps and stores notes). `Hard rules` as prominent red
chips. `Reasons` as an ordered list from `decision.reasons` in engine wording, each
expandable to the underlying signal. A `How the score was built` visual: vendor
max-risk bar, behavioural bar, blend formula rendered, composite marker, threshold
ruler — merchants trust math they can see.

**Tab 2 — Inputs (`order`, `buyer`, `payment`, `wallet`).** Four definition lists
with real fields only: asset/fiat/qty/price/created_at/side; binance_user,
verified_name, country, trade_count, completion_rate, account_age_days, device_id,
ip, chat_snippet (with matched red flags highlighted inline), risk_flags; method,
payer_name_on_account, bank_name, `acct ****1234`, ifsc, vpa, utr, amount,
credit_ts, confirmed (✓ only when independently confirmed); chain (TRC20),
deposit/withdrawal addresses (middle-ellipsis + copy), exchange.
Include the `not stored` note for full account numbers.

**Tab 3 — Sources (`vendor_calls` + `provider_verdicts`).** Table: provider,
category, status chip, risk (bar), detail text, latency, cost, `matched_list`,
`raw_ref` (external link), skipped-with-reason (`tier`). Footer: totals, cache
hits, breaker state. This is the audit tab a bank or a technical buyer reads.

**Right rail (all tabs).** `Evidence pack` card: `EV-4B1C9A7D02F1`, generated
timestamp, immutability note, `Markdown · JSON · PDF (soon)`, page preview.
`Settlement` card: voucher ref, virtual account, dedicated VPA, `pool:
quarantine`, `status: issued`, `sweep_after` countdown, reconciliation alerts
(credit landed in wrong pool / no UTR). `Counterparty history` mini-card: seen /
flagged / clean streak + last 3 verdicts + `View buyer →`. `Compliance` chips:
STR-context recorded, 194S reportable (₹50k+, 1%, indicative ₹4,525), KYC retention.
`Similar orders` link (same buyer, ±24 h).

Below tabs: **Timeline** (order created → pre-screen → voucher → credit
observed → release-gate → bot action → evidence stored), with per-node durations.

### 9.5 `/app/holds` — Step-up worklist
**Job:** clear `HOLD`s before the release window dies.

Queue list (left) + detail (right, order-summary reuse). Sort: oldest first by
default (they're the ones expiring), `Sort by value` toggle. Each row: order,
`held 41 min`, top reason, `amount at risk`. Per-order actions: run the four
`step_up` items as checkboxes; attach buyer's statement (file upload → stored with
the pack, referenced, never auto-approved); `Re-screen now` (re-fires the pipeline
against current vendor data and shows the new verdict next to the old — the "did
my evidence change the answer?" moment); `Release anyway` / `Reject`
(reason-required, audited); `Copy step-up message` (pre-written chat text for the
buyer, in plain English + Hindi). Counters: `Open 6 · Cleared today 14 · Expired
2`, `Median time to clear 22 min`. Empty state: `Nothing on hold — the guard
answered everything.`

### 9.6 `/app/buyers` — Counterparties & trust
**Job:** know your regulars, never re-meet a problem.

Table from `counterparties`: buyer key, Binance user, verified name, `seen`,
`flagged`, `clean_streak`, `last_risk`, `last_verdict`, `last_seen_at`,
+ derived `total INR traded`, `first seen`, `distinct UTRs`. Row → buyer profile:
verdict-mix donut, order list, the trust-decay explanation (`trust kept 90 days`,
velocity window 48 h), `flagged > 0` warning banner, `Watch` toggle (optional —
label it as portal-only UX, not an engine input), `Mute velocity rule` deliberately
**not offered** (policy is centralized; note it).
Search + sort by flagged/clean_streak. Empty state and the honest note: `Trust is
per-merchant; your history is yours.`

### 9.7 `/app/settlement` — Quarantine pool & vouchers
**Job:** money hygiene. Table from `settlement_vouchers`: `voucher_ref`, order,
virtual account, VPA, `amount`, `pool`, `status` (`issued` / `credited` /
`swept` / `stale`), `utr`, `credited_at`, `sweep_after` countdown. KPIs: `In
quarantine ₹`, `Awaiting sweep ₹`, `Swept 24h ₹`, `Unmatched credits` (credit with
no voucher — the dangerous bucket). Alerts list rendering `reconcile_credit`
strings verbatim. Filters by pool/status; bulk `Sweep now` for ALLOW-marked
vouchers past window (with confirm modal + audit note). Visual: two-pool diagram
(operating vs quarantine) with flows.

### 9.8 `/app/freezes` — Lien / freeze cases
**Job:** the worst day, fastest answer.

Kanban or status list from `lien_cases`: `case_ref` (`LIEN-…`), order, `utr`,
`account_no_masked`, `source` (`bank_email` / `webhook` / `manual`), `status`
(`open` / `awaiting_bank` / `submitted` / `lifted` / `rejected`), evidence
reference, created/updated. `New case` drawer: paste notice text or forward the
email, or enter UTR/order/masked account → auto-resolves to the order and pulls
the stored pack → shows `assembled: true/false` (if the order was never guarded,
say plainly what's missing). Then: `Download case file (zip)` = evidence pack +
notice + order inputs + vendor verdicts + timeline + cover letter. Add a lawyer/CA
share link (read-only, expiring) and an internal note thread.
Supporting copy: `Time is the only thing you can't get back. Sentinel keeps the
pack ready so you never rebuild it from memory.`

### 9.9 `/app/compliance` — Advisory register
Table from `compliance_events`: `event_type` (`STR_CONTEXT`, `TDS_194S`,
`KYC_RETENTION`), order, amount, payload summary, created. Cards: `STR-context
records (blocks)` · `194S reportable volume` · `KYC retention items`. Filters by
month/type. `Export for my CA (zip)` + `Monthly register (CSV)`.
**Mandatory framing:** `Advisory only. Sentinel does not compute, deduct, or file
tax or regulatory reports.` (matches `compliance.py` docstring.)

### 9.10 `/app/insights` — Ops & cost
Charts, all backed by existing metrics: decision mix over time (stacked area by
phase) · vendor latency p50/p95/p99 histogram per provider (buckets
50/100/250/500/1000/2000/4000/6000 ms) · vendor spend USD by provider (bar +
cumulative line) with `cost per order` and a `Set monthly vendor budget` control ·
rule-trigger leaderboard (which rule fires most, and how often each led to BLOCK)
· `HOLD → cleared vs expired` funnel · degraded incidents list ·
`threshold simulator`: drag BLOCK/HOLD (0.80/0.50) and see "last week this would
have changed N verdicts" — read-only unless `Apply policy` is enabled (and gated to
Book plan; backend change required, §14).

### 9.11 `/app/settings`
Sections: **Merchants** (add/rename, `merchant_id` shown as the join key) ·
**Integration** (keys list: name, created, last used, scopes, `Reveal once`,
`Revoke`; HMAC secret; transport REST/Kafka; `Sandbox` toggle; webhook/decision
consumer URL + secret; `Connection test` running a real sandbox order) ·
**Policy** (enforcement `Observe only / Enforce`, HOLD handling, tier thresholds,
fail-closed behaviour — stated as fixed and non-negotiable, shown so users
understand it, not toggled) · **Notifications** (BLOCK instant, degradation,
misrouted credit, sweep due, freeze case update — email / WhatsApp / Telegram /
webhook; quiet hours) · **Team** (seats, roles `Owner / Risk / Read`, invites) ·
**Data** (retention 12/24 months, PII fields list, `Export all my data`, `Delete`)
· **Billing** (plan, per-order usage, vendor pass-through, invoices) ·
**Security** (TOTP, IP allowlist, session list, audit log of overrides).

---

## 10. Interaction & state inventory (design every one)

**Verdict chips:** ALLOW / HOLD / BLOCK × default/hover/focus + icon +
`action` tooltip (`release/hold/reject`) + color-blind-safe `A/H/B` glyph.
**Degraded:** outline chip + `!` + tooltip naming the provider.
**Skipped (tier):** muted chip + `why`.

**Global:** streaming indicator · reconnect · `sample data` watermark on any
demo/preview mode · toast vs modal rules (destructive overrides = modal with typed
reason; exports = toast with download link) · optimistic UI never used on verdicts
(a verdict is server truth, and pretending otherwise is dangerous in a risk tool)
· per-screen undo for bulk actions (10 s) · URL-persisted filters everywhere ·
skeletons with realistic row counts, not spinners · error states name the
reason and the next action · empty states always offer `Run a sandbox decision` ·
deep links for every filter view (bank emails) · keyboard `⌘K` command palette
(orders, buyers, cases, settings) · CSV/JSON export on every table ·
per-order `Copy decision JSON`.

**Mobile (merchants live on phones):** `/app/live`, `/app/holds`, `/app/orders`
are the three screens that must work one-handed; push/notify for BLOCK and freeze
cases; never require a table for a decision.

**A11y:** WCAG 2.2 AA. Contrast minimums (red/amber chips fail on dark — use
tokens in §11). Tables real `<th scope>` + row headers. Focus ring 2 px, visible
on chips. Live feed `aria-live="polite"` (never assertive — it streams constantly).
Respect `prefers-reduced-motion` (verdict settle animation off). Charts get data
tables. Touch targets 44 px. Colour never alone: verdict has text + icon.

**i18n:** English default; **Hindi** for buyer-facing step-up messages and
freeze-case cover letters (that text goes to a bank/police inbox, so locale
matters). `en-IN` number and date formatting. Currency `₹` Indian digit
grouping; USD only for vendor cost.

---

## 11. Design system (paste into Stitch as `design.md`)

**Brand idea.** A scanner, not a scoreboard. Clinical calm for people making
fifteen-minute money decisions.

### 11.1 Color
| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink-900` | `#0B1220` | `#F4F7FB` | Primary text |
| `--ink-600` | `#4A5568` | `#9AA7B8` | Secondary |
| `--surface-0` | `#FFFFFF` | `#0E1418` | App background |
| `--surface-1` | `#F6F8FA` | `#151D23` | Cards / table stripes |
| `--line` | `#E3E8EF` | `#243038` | Borders |
| `--brand-700` | `#163E63` | `#7FC0F0` | Wordmark, links, primary |
| `--allow-600` | `#0F7B4F` | `#3DD68C` | ALLOW chip, positive |
| `--hold-600` | `#8A5A00` | `#F5B301` | HOLD chip, caution |
| `--block-600` | `#B3261E` | `#FF6B5E` | BLOCK chip, danger |
| `--degraded-600` | `#5B3FA8` | `#B39DFF` | Vendor-degraded state |
| `--quarantine-600` | `#0B6B7A` | `#4FD1E5` | Pools, vouchers |

Dark mode is a **first-class** requirement (desks run wallboards and 2 a.m.
shifts); both themes must ship in the mockup set. Never signal verdict with hue
alone.

### 11.2 Type
`Inter` UI + `IBM Plex Mono` for ids/UTRs/hashes/JSON + `Newsreader` (serif) for
**only** two things: the landing H1 and the rendered evidence-pack document (it must
read as a legal artefact, not a dashboard). Scale: 12/13/14/16/20/24/32/44; tight
1.15 leading on data, 1.6 on prose; tabular-nums on every number; ids
never broken across lines.

### 11.3 Spacing / shape / elevation
4 px grid, spacing tokens 4/8/12/16/24/32/48. Radius 6 (chips 999, cards 8,
modals 12). Borders 1 px `--line` preferred over shadows; one elevation level for
popovers (y2 blur12 12%) and one for modals. Data density: **compact default**
(rows 36 px) with a `Comfortable` toggle — merchants scan hundreds of orders.

### 11.4 Components inventory (design once, reuse)
Verdict chip · Risk bar (0–1, threshold ticks at .5/.8) · Confidence meter ·
Rule chip (hard vs soft) · Phase chip · Degraded/Unavailable/Skipped status pill ·
Money (`₹` Indian grouping + crypto sub-line) · Mono id with copy · Countdown
(`sweep_after`) · Timeline (gated order) · Verdict card · Data table (sticky,
filterable, bulk) · Filter drawer + chip list · Saved-view tabs · Sparkline ·
Stacked verdict bar · Histogram · Donut (verdict mix) · Area-over-time · Code block
with tabs (Python/Node/cURL/JSON) · Key vault (reveal-once) · Evidence document
preview (serif, page shadow) · Step-up checklist · Override confirm with typed
reason · Empty/error/loading/degraded states · Toast · Side drawer · Command
palette · Live feed row · Kanban status card · Pool diagram · Simulator slider.

### 11.5 Landing-page visual rules (anti-generic)
No stock traders, no glowing shields, no globe-and-lines network art, no 3D coins,
no centered-hero-with-gradient-blob. Use: real product surfaces (screenshots of
§9), the money-flow diagram (§6.4), the rendered evidence document (§7.3), the
two-gate timeline (§6.5), and the raw `GuardDecision` JSON. Motion: one choreographed
sequence — order arrives → signals light up → score builds → `BLOCK` → evidence
pack prints — 6 s, `prefers-reduced-motion` shows the final frame.

---

## 12. Voice rules for every string on the site

1. Verdict first, number second, feeling never.
2. Say what the system *did*, not what it *can* do (`Blocked ₹18,40,000 today`,
   not `Prevents fraud`).
3. Name the mechanism when giving reassurance (`Because the credit carries a UTR
   mapped to voucher VCH-…, you can prove which order it belonged to`).
4. Never say `AI-powered`, `next-generation`, `seamless`, `revolutionary`,
   `unparalleled`, `end-to-end encryption of everything`.
5. Always distinguish advisory vs filing (§9.9) and guarded vs not-guarded (§9.3).
6. Regulatory references are contextual, never legal advice (PMLA, Cyber-TAT/N4C,
   Section 91 CrPC, 194S, FIU-IND) — and keep a disclaimer adjacent.
7. Hindi strings exist only for buyer-facing and bank-facing templates.

---

## 13. Events to instrument (the site must measure its own story)

`hero_cta_click`, `verdict_demo_tab_view`, `pricing_calc_run`,
`signup_start/complete`, `wizard_step_1..5_view/complete`, `key_created`,
`sandbox_decision_run` (strongest activation signal), `bot_connected_first_live_order`,
`hold_opened`, `step_up_item_checked`, `evidence_download`,
`freeze_case_opened`, `csv_export`, `override_confirmed`,
`observe_only_off` (enforcement adopted), `day_7_activation` (≥1 real order).
North star: **orders screened per active merchant per day.** Activation: first live
verdict within 48 h of signup.

---

## 14. Backend status — what the portal can call today

**The portal API is now built.** Full contract with captured real responses:
**[PORTAL_API.md](PORTAL_API.md)**. Run it with
`python -m src.portal.dev_server --seed` (no Docker needed).

Implemented under `/api/v1/…`:

| Surface | Paths |
|---|---|
| Auth + workspaces | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`, `POST /auth/merchants` |
| Connection wizard | `GET/POST/DELETE /integration/keys`, `GET /integration/status`, `POST /integration/test` (real decision, nothing persisted) |
| Ledger | `GET /portal/orders`, `/orders/export` (CSV), `/orders/{id}`, `/orders/{id}/evidence`, `POST /orders/{id}/override`, `/holds` |
| Buyers / settlement / freezes / register | `/counterparties`, `/counterparties/{key}`, `/vouchers`, `GET+POST /liens`, `PATCH /liens/{ref}`, `/compliance-events` |
| Aggregates | `/overview`, `/insights`, `/stats/summary` |
| Live feed | `GET /portal/feed` (SSE, id-cursor, `once=true` fallback) |

Portal writes live at **`/portal/*`, not `/p2p/*`**, because
`HmacAuthMiddleware` guards POSTs under `/api/v1/p2p/` for the bot. Scoping is
enforced per session (`merchant_memberships`), roles are `owner` / `risk` /
`read`, and out-of-scope objects return 404 rather than confirming existence.

Built while wiring this, in the process fixing real defects:

- `p2p_orders` was unique on `order_id`, so **the release-gate decision of every
  order failed to persist** and took its evidence bundle with it. Now unique on
  `(order_id, phase)`; re-screening a gate updates the row instead of colliding.
- `evidence_bundles.reference` was derived from `order_id` alone, so the two
  gates collided on a unique column. Now derived per decision.
- `vendor_calls` and `compliance_events` were unattributed, so a two-gate order
  reported double spend. Both carry `phase` now.
- `lien_cases` gained `merchant_id`; a duplicate notice updates the case instead
  of silently failing to save.
- Unauthenticated `GET /p2p/orders/{id}/evidence` (buyer names, UTRs, masked
  accounts by enumerable id) is gone; the pack is served authenticated + scoped.
- Schema layer: reserved `EntityGraph.metadata` attribute, a duplicate
  `ix_merchants_status` index that broke `create_all` (and therefore app startup),
  BIGINT PKs that cannot autoincrement on SQLite, `now()` defaults that SQLite
  rejects, and `alembic/env.py`'s self-assignment + async-connection wiring.
  `DATABASE_URL` was being ignored because `Settings` was case-sensitive.

Still open (so mockups do not promise them):

| Capability | Status |
|---|---|
| Evidence **PDF** export | Not built — `formats` is `["markdown","json"]` |
| Voucher **sweep** action, misroute acknowledgement | Read-only |
| Statement upload on a HOLD, case note threading | Not built |
| Notification routing, billing, team invites, IP allowlist | No endpoints |
| Per-merchant policy overrides (BLOCK/HOLD thresholds) | Hardcoded in `fusion.py`; simulator is read-only |
| Landing-page "blocked today across merchants" ticker | No cross-merchant aggregate — keep it labelled illustrative |
| Marketing pages (`/`, `/pricing`, `/docs`…) | Frontend work; this document is the content source |

---

## 15. Stitch prompt pack (paste in this order)

> Each prompt is self-contained on purpose — Stitch sessions don't share context.
> Prepend §11 tokens to every prompt, or upload §11 as `design.md` first.

1. `Landing hero for "Sentinel", a pre-settlement AML guard for Binance P2P
   USDT/INR merchants selling crypto for rupees in India. H1 "One dirty credit can
   freeze your whole account." Sub: screens buyer before payment and rupees before
   settlement, returns ALLOW/HOLD/BLOCK in seconds with an evidence pack. Left
   copy + CTAs "Connect your bot" / "See a real decision". Right: a verdict card
   settling to BLOCK showing risk 0.93, confidence 0.90, hard rule mule_account,
   third-party payer "Sunil Verma" ≠ Binance KYC "Ramesh Kumar", UTR
   429177651234. Dark navy/ink palette, teal-green ALLOW / amber HOLD / red BLOCK
   chips, IBM Plex Mono for ids, Inter for UI. No stock traders, no shields, no
   3D coins. Desktop + mobile.`
2. `Landing section "How a freeze happens": horizontal money-flow diagram Victim →
   Mule → Buyer's bank account → Merchant's bank account → LIEN with the last two
   edges red and a Sentinel gate glyph labelled "you decide here". Copy: "The
   danger isn't the crypto. It's the credit." Three stat cards: 15-minute release
   window, one credit freezes the whole account, unfreezing needs evidence made in
   advance.`
3. `Landing section "Two gates": timeline of a P2P order with PRE-SCREEN (before
   INR is accepted) and RELEASE-GATE (before USDT leaves escrow), plus two cards
   listing real inputs — buyer: binance_user, verified_name, trade_count,
   completion_rate, account_age_days, chat_snippet; payment: method,
   payer_name_on_account, acct ****1234, ifsc, vpa, utr, amount, credit_ts,
   confirmed; wallet: TRC20 deposit/withdrawal addresses. Mention per-order
   quarantine voucher VCH- with its own virtual account and VPA.`
4. `Interactive three-tab verdict block: ALLOW / HOLD / BLOCK decision cards for
   order ord_9f3c71, release-gate, 5,000 USDT = ₹4,52,250, risk, confidence,
   hard-rule chips, reasons list, step-up checklist (HOLD shows 4 items), vendor
   spend $0.42, latency 1240 ms, evidence ref EV-4B1C9A7D02F1, bot action
   release/hold/reject.`
5. `Signal grid: 11 chips for sanctions_hit, mule_account, wallet_exposure,
   third_party_payment, freshness, velocity, structuring, amount_deviation,
   deal_red_flags, repeat_flagged, and mitigating clean_streak — each with a
   one-line trigger and a weight bar. Compact, clinical, no icons of padlocks.`
6. `Section "Someone else paid. That's the freeze.": two receipt-style cards side by
   side, Payer Ramesh Kumar = Buyer ✓ (allow tint) vs Payer Sunil Verma ≠ Buyer ✗
   (block tint), copy about Binance appeal rule and BLOCK at confidence 0.90.`
7. `Section "Fail closed": diagram vendor timeout → degraded verdict → HOLD + named
   provider, with the literal reason string "Required vendor unavailable -
   degraded, refusing to auto-allow". Bullets: 6s latency budget, circuit breakers,
   2 retries, caching.`
8. `Section "The pack you hand the bank": realistic evidence document rendered in
   serif on a page — header "Sentinel Evidence Pack EV-4B1C9A7D02F1", order,
   phase, verdict BLOCK (reject) risk/confidence, sections Order, Buyer, Payment
   credit, Vendor signals, Hard rules triggered, Reasons — plus Download
   Markdown / JSON buttons and a note "full account numbers never stored, last 4
   only".`
9. `Pricing page, 4 tiers: Sandbox free / Desk ₹9,999/mo + ₹1.50 per screened order
   / Book ₹34,999/mo + ₹1.10 / Enterprise. Notes: vendor pass-through visible per
   call, daily spend caps, no % on volume. Reassurance strip: No custody, No
   trading keys, Last-4 account storage only, Delete my data.`
10. `Signup + magic-link login, then a 5-step "Connect your automation" wizard:
   1 Identity (merchant_id) 2 Credentials (guard key + reveal-once HMAC secret)
   3 Transport (REST two endpoints vs Kafka sentinel.p2p.order /
   sentinel.p2p.decision) 4 Test with mock data (live GuardDecision JSON)
   5 Go live (Observe only → Enforce). Right panel shows what the bot will see.
   Include the signature-mismatch 401 error state.`
11. `Portal home /app/overview: 5 KPI cards with sparklines (orders screened, INR
   blocked ₹18,40,000, INR released, auto-cleared %, median decision time), stacked
   ALLOW/HOLD/BLOCK mix bar split by phase, "Needs you" queue of HOLD orders with
   age badges (15-min window), risk histogram 0-1 with threshold markers at 0.50
   and 0.80, top exposures table, quarantine pool summary with sweep countdown,
   vendor spend strip. Dark mode variant. Compact density.`
12. `/app/live streaming guard feed: newest-first verdict capsules (time IST, order
   id, phase chip, ₹ amount, buyer, verdict chip, risk bar, confidence, latency,
   degraded icon, hard-rule chips, Open), pause / jump-to-newest controls, filters
   incl. min-risk slider, right side panel of provider health with status pills ok
   / unavailable / error / skipped, p95 latency, circuit-breaker state, cache hit
   rate, and a disconnected fallback state.`
13. `/app/orders transaction history: dense table (order, decided, phase,
   ₹ ticket + USDT qty, buyer, verdict, risk 0.93 bar, confidence, rule chips,
   masked payer + UTR, method, voucher pool, evidence link, degraded, spend,
   latency), left filter drawer with 13 filters incl. hard-rule multi-select,
   saved views, bulk export CSV + zip evidence, analytics header that recomputes
   with filters ("1,284 orders · 96 BLOCK · ₹18.4L blocked · median 1.18s"), deep
   linkable URL, and a row state "not screened by Sentinel" for pre-onboarding
   orders. Add the no-results and 10k-row states.`
14. `/app/orders/{id} order detail, the single most important screen: header band
   with BLOCK chip, reject action, ₹4,52,250 (5,000 USDT @ ₹90.45), buyer, decided
   time, risk 0.93, confidence 0.95, latency, spend, evidence ref; tabs Why /
   Inputs / Sources; "Why" shows hard-rule chips, reasons, step-up checklist with
   mark-done, and a visual score build-up (vendor max-risk bar + behavioural bar +
   blend formula + threshold ruler); "Inputs" lists order/buyer/payment/wallet
   fields with masked account ****1234 and chat snippet red-flags highlighted;
   "Sources" table of vendor calls (provider, category, status, risk, detail,
   latency, cost, matched list, raw ref, tier-skipped reason) with totals; right
   rail sticky cards for evidence pack (MD/JSON/PDF-soon), settlement voucher with
   sweep countdown and misroute alert, counterparty history, compliance chips
   (STR_CONTEXT, TDS_194S 1% indicative, KYC_RETENTION); gated-order timeline below;
   "Override & release" destructive modal requiring a typed reason.`
15. `/app/holds step-up worklist, split view: queue sorted oldest-first with
   "held 41 min" and ₹ at risk, right pane with the 4 step-up items as checkboxes,
   statement upload attached to the evidence pack, "Re-screen now" showing new
   verdict next to the old, Release anyway / Reject with reason, copyable buyer
   message in English + Hindi, counters Open/Cleared/Expired/Median time to clear,
   empty state.`
16. `/app/buyers counterparty table (seen, flagged, clean_streak, last_risk,
   last_verdict, last_seen, INR traded, distinct UTRs) + buyer profile drawer with
   verdict-mix donut, order list, 90-day trust decay note, and a Watch toggle.
   Show a flagged>0 warning banner.`
17. `/app/settlement quarantine screen: two-pool diagram (operating vs
   quarantine), voucher table (voucher_ref VCH-, order, virtual account, VPA,
   amount, pool, status issued/credited/swept/stale, utr, credited_at, sweep_after
   countdown), KPIs in-quarantine ₹ / awaiting-sweep ₹ / swept 24h ₹ / unmatched
   credits (dangerous bucket), and misroute alert rows like "credit for order
   ord_9f3c71 landed in pool 'operating', not quarantine" plus "has no UTR to
   trace". Teal accent for pool semantics.`
18. `/app/freezes lien case workspace: status board open / awaiting_bank /
   submitted / lifted / rejected, New case drawer taking pasted notice text or UTR
   / order / masked account and auto-assembling the evidence pack (show
   "assembled: false — this order was not guarded" honestly), Download case file
   (zip) with cover letter + pack + verdicts + timeline, expiring read-only share
   link for bank/CA, internal notes.`
19. `/app/compliance advisory register: STR_CONTEXT / TDS_194S / KYC_RETENTION
   table with amounts and payload summaries, summary cards, monthly CSV, "Export
   for my CA" zip, and a prominent always-visible line "Advisory only — Sentinel
   does not compute, deduct, or file tax or regulatory reports".`
20. `/app/insights ops charts: decision mix stacked area by phase, vendor latency
   p50/p95/p99 histogram per provider with buckets 50-6000ms, vendor spend bars +
   cumulative USD line with cost-per-order and a monthly budget control, rule
   trigger leaderboard with block attribution, HOLD cleared-vs-expired funnel,
   degraded incident list, and a threshold simulator slider (BLOCK 0.80 / HOLD
   0.50) showing "last week N verdicts would change".`
21. `/app/settings integration section: guard keys table (name, created, last
   used, scope, reveal-once, revoke), HMAC secret block with the exact header
   formula X-Sentinel-Signature = hex(hmac_sha256(secret, "{timestamp}." + body))
   and 300s tolerance, REST vs Kafka transport toggle with copyable snippets,
   Observe-only vs Enforce switch with a warning modal, connection test running a
   sandbox order and printing the real decision JSON, plus Policy (fixed
   fail-closed, read-only with explanation), Notifications (BLOCK, degradation,
   misrouted credit, sweep due, freeze case), Team roles Owner/Risk/Read, Data
   retention + export/delete, Billing usage, Security audit log of overrides.`
22. `Mobile variants of /app/live, /app/holds and an order summary card — one-handed,
   verdict legible in sunlight, cards instead of tables, push-notification style
   BLOCK alert. Same palette, comfortable density.`
23. `Design-system page for Sentinel: color tokens (ink/surface/line/brand +
   allow/hold/block/degraded/quarantine in light and dark), type scale Inter +
   IBM Plex Mono + Newsreader for evidence documents and the landing H1 only,
   4px spacing scale, radii, verdict chips in all states, risk bar with 0.50/0.80
   ticks, phase chips, provider status pills, money in Indian grouping,
   skeletons, empty/error/degraded states, compact table row 36px.`

---

## 16. Build sequence for mockups (what to generate first)

| Priority | Screens | Why |
|---|---|---|
| P0 | §6 landing hero + gates + verdict walkthrough · `/app/orders` + `/app/orders/{id}` · connection wizard | These four carry the pitch *and* the daily job; every other screen reuses their components |
| P1 | `/app/overview` · `/app/live` · `/app/holds` | Live-monitoring story merchants ask for in demos |
| P2 | `/app/freezes` · `/app/settlement` · evidence page | Differentiators that justify price |
| P3 | `/app/buyers` · `/app/compliance` · `/app/insights` · `/app/settings` | Depth |
| Always | Dark mode + mobile for every P0/P1 screen | Wallboards, night desks, phone-first merchants |
