# Sentinel UI — build map & 21st.dev workflow

Companion to [WEBSITE_CONTENT_BRIEF.md](WEBSITE_CONTENT_BRIEF.md) (what each
screen says) and [PORTAL_API.md](PORTAL_API.md) (what each screen reads).
This file is the **component queue**: what we build, in what order, and which
21st.dev component to pull for each slot.

---

## 1. Where things live

| | |
|---|---|
| Frontend | `web/` — Next.js 16 (App Router), TypeScript, Tailwind v4, shadcn layout (`components/ui`, `@/lib/utils`) |
| Backend | FastAPI on `:8000`. Dev without Docker: `python -m src.portal.dev_server --seed` |
| Installed | `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `tw-animate-css` |
| Primitives in place | `button.tsx` (+ `buttonVariants`), `menu-toggle-icon.tsx`, `use-scroll.ts`, `sentinel-logo.tsx`, `kinetic-grid.tsx`, `header-2.tsx` |
| Tokens | `app/globals.css` — Sentinel palette (brief §11) **plus shadcn's semantic layer** (`background/foreground/primary/secondary/muted/accent/border/input/ring/destructive`), dark-only so far |
| Fonts | `app/layout.tsx` — Inter (UI) · IBM Plex Mono (ids, UTRs) · Newsreader (headline + evidence documents only) |

The shadcn semantic layer is not optional: components from 21st.dev are written
against `bg-background` / `border-border` / `bg-accent`, and without those tokens
defined a dropped-in component renders with invisible surfaces and no borders.
Each is mapped to a Sentinel value, so there is still one source of truth.

```bash
cd web && npm install
npm run dev            # http://localhost:3000  (hot reload)
npm run build          # type-checks + production bundle
```

---

## 2. The loop we're running

1. **I name a slot** (below, in order) with the exact content it must carry.
2. **You send the component** — paste from 21st.dev, or the search query and I'll
   pull it myself once the CLI is authenticated (§3).
3. **I integrate it**: drop into `web/components/ui/`, wire the real content and
   API types, keep the component source intact where possible, and note any local
   deviation in a header comment so a future 21st version can be pasted over it.
4. **I verify** with `npm run build` + a rendered screenshot before asking for the
   next one.

Rules I'm holding to, from the brief:

- Verdict colour never carries meaning alone — chip = colour + text + icon.
- `risk_score` / `confidence` are 0–1 floats (`0.93`, not `93/100`).
- Money is a raw number; `₹4,52,250` Indian grouping happens in the view.
- Timestamps arrive ISO-8601 with an offset; render IST, tooltip UTC.
- No stock traders, no glowing shields, no 3D coins, no gradient blobs.
- Every animated surface respects `prefers-reduced-motion`.

---

## 3. Connecting me to 21st.dev

I can reach the catalog myself through the official CLI — `@21st-dev/cli`
(installed and verified working here). It only needs auth, which I can't do for
you:

```bash
# Option A — browser sign-in (recommended; the key is stored by the CLI, not in this repo)
npx @21st-dev/cli login
npx @21st-dev/cli whoami

# Option B — API key for this shell only (never commit it, never paste it into a file)
export TWENTYFIRST_TOKEN=21st_sk_…
```

Then I can run the whole loop without you copy-pasting:

```bash
npx @21st-dev/cli search "pricing table" --limit 8     # browse
npx @21st-dev/cli get <id>                             # read the code + demo
npx @21st-dev/cli add <author>/<slug>                  # install into web/components/ui
npx @21st-dev/cli logo "binance"                       # brand marks (works without login)
```

**Optional MCP server** (same catalog, persistent tool access instead of a CLI
call per query): add `https://21st.dev/api/mcp` to Qoder's MCP settings with your
`x-api-key`. Run `npx @21st-dev/cli init --client <editor>` to generate the exact
snippet — it merges into existing MCP config rather than overwriting it. Until
either of those is done, keep pasting components; that path works fine.

---

## 4. Component queue

Done ✅ · Next up ▶️ · Later ○

| # | Slot | Content it must carry (brief §) | What to search on 21st | Status |
|---|---|---|---|---|
| 1 | Page background | Fixed interactive canvas behind the whole landing page | `kinetic grid background` | ✅ `components/ui/kinetic-grid.tsx` |
| 2 | **Header / nav** | Logo, `How it works · Integrations · Evidence · Pricing`, `Log in` + `Connect your bot`, mobile menu (§6.1) | `header`, `navbar with mobile menu` | ✅ `components/ui/header-2.tsx` |
| 2b | Hero shell | Eyebrow, H1, subhead, 2 CTAs, microcopy, provider strip (§6.2–6.3) | `hero`, then replace with a 21st hero if you prefer | ✅ provisional |
| 3 | **Verdict card** | The `GuardDecision`: `ord_9f3c71`, `release-gate`, `5,000 USDT → ₹4,52,250`, `BLOCK`/`reject`, risk `0.93`, confidence `0.90`, hard rule `mule_account`, payer `Sunil Verma ≠ Ramesh Kumar`, UTR, `1240 ms · $0.42`, `EV-4B1C9A7D02F1` (§6.2, §6.6) | `status card`, `terminal card`, `detail card with badge` | ▶️ |
| 4 | **Freeze anatomy diagram** | `Victim → Mule → Buyer's account → YOUR account → LIEN`, last two edges red, gate glyph labelled "you decide here" (§6.4) | `stepper`, `flow diagram`, `timeline horizontal` | ▶️ |
| 5 | **Two-gates timeline** | Lifecycle with `PRE-SCREEN` and `RELEASE-GATE` inserted, plus the two input/output cards (§6.5) | `timeline`, `steps vertical`, `comparison cards` | ○ |
| 6 | **Verdict tabs** | `ALLOW / HOLD / BLOCK` walkthrough; HOLD must list the four real `step_up` lines (§6.6) | `tabs`, `toggle group` | ○ |
| 7 | **Signal grid** | 11 rule chips with trigger + weight bar, incl. the mitigating `clean_streak` chip (§6.7) | `feature grid`, `tag chips`, `progress list` | ○ |
| 8 | Third-party block section | Two receipts: `Payer = Buyer ✓` vs `Payer ≠ Buyer ✗` (§6.8) | `pricing card pair`, `comparison split` | ○ |
| 9 | Fail-closed section | `vendor timeout → degraded → HOLD` + the literal reason string (§6.9) | `code block`, `flow`, `alert card` | ○ |
| 10 | **Evidence pack** | The rendered markdown pack in serif on a page + `Download MD/JSON` (§6.10, §7.3) | `document viewer`, `paper card`, `markdown preview` | ○ |
| 11 | Integration tabs | `REST / Kafka / Signed requests` with the Python snippet (§6.12) | `code tabs`, `syntax highlighter` | ○ |
| 12 | **Portal preview** | Screenshot frame of `/app/overview` with 4 stat captions (§6.13) | `browser frame`, `screenshot mockup` | ○ |
| 13 | Audience cards | Solo / desk / bot-builder, each with first-click path (§6.14) | `pricing cards`, `feature cards` | ○ |
| 13b | **Testimonials** | Merchant voices bento (§6.14 social proof) — illustrative until consented, see §7 | `testimonial bento`, `reviews grid` | ✅ `components/ui/testimonial.tsx` |
| 14 | **Pricing table** | Sandbox · Desk · Book · Enterprise + per-order calculator (§6.15, §7.4) | `pricing table`, `pricing with toggle` | ○ |
| 15 | FAQ | 9 real objections (§6.16) | `accordion`, `faq` | ○ |
| 16 | Footer + final CTA | Legal strip, disclaimer (§6.17) | `footer`, `cta band` | ○ |
| 17 | Marquee | Provider logos / rule changelog ticker | `marquee`, `infinite scroll logos` | ○ |

### Portal (after the landing page)

| # | Screen | Primary components needed |
|---|---|---|
| P1 | App shell — left rail, workspace switcher, `⌘K`, live status pill | `sidebar`, `command menu`, `combobox`, `avatar` |
| P2 | `/portal/overview` — 5 KPI cards + sparklines, verdict mix bar, needs-you queue, risk histogram, quarantine strip | `stat card`, `sparkline`, `bar chart`, `area chart`, `list rows` |
| P3 | `/portal/live` — streaming capsules + provider health panel | `activity feed`, `table virtual`, `badge dot` |
| P4 | `/portal/orders` — the ledger: 13 filters, chip row, bulk select, CSV | `data table`, `filter drawer`, `multi select`, `date range` |
| P5 | `/portal/orders/{id}` — Why / Inputs / Sources tabs + evidence, voucher, buyer, compliance rail + timeline | `tabs`, `description list`, `timeline`, `drawer`, `code viewer` |
| P6 | `/portal/holds` — queue + step-up checklist, re-screen, override modal | `checklist`, `split view`, `dialog`, `file upload` |
| P7 | `/portal/freezes` — case board + case-file download + share link | `kanban`, `dialog`, `copy link` |
| P8 | `/portal/settlement` — two-pool diagram, voucher table, sweep countdown | `stat card`, `countdown`, `table` |
| P9 | `/portal/buyers`, `/portal/compliance`, `/portal/insights` | `table`, `donut`, `histogram`, `slider` |
| P10 | `/setup` — 5-step connect-your-bot wizard with live preview panel | `stepper`, `code block`, `copy field`, `toggle` |

---

## 5. Data wiring notes for whoever asks

- Everything above renders from the shapes in `docs/PORTAL_API.md` §5. When a
  component goes into the portal, it gets a typed client in `web/lib/api.ts`
  (`NEXT_PUBLIC_API_BASE_URL`, Bearer token from the session) — no `any`s, and
  the response types mirror the Pydantic models so a backend rename breaks the
  build instead of the page.
- `not_screened`, voucher `sweep_after`, and `degraded` are the three fields most
  likely to be forgotten in a mockup; they exist in the API and each needs a UI
  state.

### Micro-interactions applied

| Component | Where it's used | Settings chosen, and why |
|---|---|---|
| `VariableFontCursorProximity` (`registry/default/motion/…`) via `ProximityNav` | Desktop header nav only | `radius=90`, `'wght' 400 → 700`, exponential falloff. The demo's 300→800 at `text-xl` is a display-size effect; at 13px, 300 reads thin and 800 reads broken, so the range is narrowed. Mobile menu stays plain — the effect is pointer-driven and adds nothing to touch. |

Verified by measurement, not by eye: with the pointer over "How it works" its glyphs reach
`wght 682` while "Pricing" holds at the `400` base; move to "Pricing" and it climbs to `673`
while the first settles back down.

### Component sources

`m-variable-font-cursor-proximity-3` shipped its demo but not the registry primitive it
imports, so `registry/default/motion/variable-font-cursor-proximity.tsx` is implemented
against the same public API (`containerRef`, `radius`, `falloff`,
`from/toFontVariationSettings`). Once `21st login` is done, `npx @21st-dev/cli get <id>`
can replace that file with the upstream one without touching any call site.

---

## 6. Integration gotchas learned so far

Each of these silently produced a wrong-looking result once; they will recur.

| Gotcha | What it breaks | Fix already in place |
|---|---|---|
| `KineticGrid`'s root is `overflow-hidden` | Any `position: sticky` child (the header) stops sticking — the clipping div becomes the scroll container | Page passes `className="overflow-visible"` to `KineticGrid` |
| Missing shadcn semantic tokens | `bg-background`, `border-border`, `bg-accent` resolve to nothing → invisible surfaces, no borders | Token block added to `globals.css`, mapped to Sentinel colours |
| `animate-in` / `zoom-in-95` classes | Menus open with no transition, looking unfinished | Installed `tw-animate-css` and imported it after `tailwindcss` |
| Component imports a hook/icon file not included in the paste | Build fails on `use-scroll`, `menu-toggle-icon` | Written by hand, matching the props the caller passes |
| Font isn't variable | `font-variation-settings` is applied and silently does nothing — no error, no visual | Check the built CSS for `font-weight: 100 900` on the `@font-face`. Inter is loaded without a `weight` option (variable); IBM Plex Mono and Newsreader are pinned to static weights, so they cannot do axis animation |
| `pkill -f "next start"` | Doesn't match the real process name (`next-server`), so a stale build keeps the port and you verify the *old* page | Kill by PID from `lsof -nP -iTCP:<port> -sTCP:LISTEN`, and confirm the served HTML changed before believing a screenshot |
| `next dev` in the sandboxed preview browser | HMR websocket is blocked → no hydration → canvas components never paint | Verify against `npm run build && npm start`; `npm run dev` is fine in a normal browser |
| Browser cache on `next start` | `/` is prerendered, so a rebuild can still show the previous page and a `querySelector` probe looks like a broken component | Navigate with a cache-busting query (`/?v=2`) before concluding anything is missing |

---

## 7. Testimonials: what may be published

The `testimonial.tsx` section ships with **illustrative personas, not
customers**, and each entry carries `consented: false`. While any entry is
unconsented, the section renders a "Sample copy. Not customer statements." line
and an `ILLUSTRATIVE` tag on the card. Flip `consented: true` per entry as real
permission arrives; the disclosure disappears when every entry is true.

**Why the rule exists.** Attributing an invented quote to a real, named Binance
P2P merchant is a false statement of endorsement. That is misleading advertising
under the Consumer Protection Act 2019 rules and the ASCI Code, it is actionable
by the person named, and it is fatal to a product whose entire offer is that its
claims are traceable to evidence. A reviewer who checks one quote and finds the
merchant never said it invalidates every other claim on the page.

**What counts as consent.** Written, per person: the exact quote as it will
appear, the identity string (name or merchant handle), their role, and the date.
Store it next to the copy — a reply in a chat thread is enough, a screenshot of
it is better.

**How to get real ones, in order of ease.**

1. **Your own pilot desks.** The seed merchant and anyone you have run the guard
   with. Ask for one specific moment, not a general compliment — "what happened
   on the order you remember best" produces usable copy.
2. **Case stories from real ledger data, with permission.** The strongest
   testimonial for this product is a sequence: `HOLD → step-up → cleared inside
   the window`, or `BLOCK on a third-party payer → ₹4.5L never entered the
   account`. Pull it from `/api/v1/portal/orders/{id}` with the merchant's
   approval and the pack becomes the proof.
3. **Anonymised aggregate.** "Across N desks, ₹X lakh of credits were blocked
   before settlement last month" — truthful without naming anyone. Needs the
   cross-merchant aggregate that does not exist yet (see §14 of the content
   brief), so do not publish it until it does.
4. **Your own editorial voice.** The last card ("Nothing here is a promise that
   an account will never be frozen…") is Sentinel speaking, not a customer, so it
   is marked consented and carries no attribution. Keep that distinction.

**Do not** use stock photos as testimonial faces. The component uses monogram
tiles; `photo` accepts a portrait from `/public` only when there is a real
person who agreed to appear.
