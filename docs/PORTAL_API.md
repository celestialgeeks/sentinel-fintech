# Sentinel Portal API — frontend contract

The HTTP surface the merchant portal is built against. Every example below was
captured from a running server against seeded data, not written by hand.

Companion documents: [WEBSITE_CONTENT_BRIEF.md](WEBSITE_CONTENT_BRIEF.md) holds
the screen-by-screen product spec; §14 of that file maps each screen to the
endpoints here.

---

## 1. Run it

```bash
# 1. Portal API + demo merchant, no Docker required
python -m src.portal.dev_server --seed

#    → http://127.0.0.1:8000        (OpenAPI at /docs)
#    → login: demo@sentinel.dev / demo-passw0rd-123
#    → merchant_id: default

# 2. Production shape (Postgres + Redis + Kafka via docker compose)
docker compose up -d
alembic upgrade head
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

| Flag | Meaning |
|---|---|
| `--port`, `--host` | Bind address (default `127.0.0.1:8000`) |
| `--seed` | Create the demo merchant and ~24 real guard decisions |
| `--reset-seed` | Wipe that workspace's history and re-seed |
| `--db URL` | Override `DATABASE_URL` (default `sqlite+aiosqlite:///./sentinel_dev.db`) |

The dev server mounts the same routers as production. What differs is
infrastructure only: vendors without an API key fall back to the deterministic
mocks in `src/vendors/mock.py`, and `guard_state` (velocity, counterparty trust)
uses its in-process cache instead of Redis. Same verdicts, same fields, same
status codes.

The dev seed also backfills plausible `latency_ms` / `cost_usd` on vendor calls
and prints that it did so — mock providers make no network call, so the real
numbers are genuinely 0 and the Insights screen would render empty. Those
columns are demo data **only** in a seeded database; against keyed vendors they
are measured.

---

## 2. Two surfaces, two auth schemes

| Surface | Path prefix | Auth | Who |
|---|---|---|---|
| Bot gates | `/api/v1/p2p/*` | `X-Sentinel-Signature` HMAC when `GUARD_HMAC_SECRET` is set | The merchant's trading automation |
| Portal | `/api/v1/auth/*`, `/api/v1/integration/*`, `/api/v1/portal/*` | `Authorization: Bearer <jwt>` | The human |

Portal writes live under `/portal` **on purpose**: `HmacAuthMiddleware` guards
POSTs under `/api/v1/p2p/`, so a browser session and a signed bot call can never
trip over each other.

Tokens are HS256 JWTs (`sub` = user id, `typ: "sessions"`, `exp`/`nbf`/`iat`),
signed with `JWT_SECRET` and valid for `JWT_EXPIRE_MINUTES` (default 1440).
Send it as `Authorization: Bearer …`. Outside production, an unset `JWT_SECRET`
generates an ephemeral per-process key (sessions end on restart); in production
it refuses to start rather than mint forgeable sessions.

### Scoping model

A session resolves to a set of `merchant_key` values via `merchant_memberships`.
Every read filters `WHERE merchant_id IN (that set)`. Roles are `owner`, `risk`,
`read`:

- `read` and `risk` may read everything in the workspace and record a
  `hold`/`reject` override.
- only `owner` may record a `release` override, create or revoke a key, or file a
  freeze case.
- Asking for a workspace you do not belong to is `403`. An object that is not in
  your scope is `404` — the API never confirms it exists somewhere else.

---

## 3. Errors

| Code | When | Body |
|---|---|---|
| `401` | Missing, expired, tampered or wrong-secret token | `{"detail": "…"}` |
| `403` | Not a member of `?merchant=`, or role not allowed to act | `{"detail": "only an owner may override a decision to release; risk and read roles cannot"}` |
| `404` | Unknown order / case, or belongs to another merchant | `{"detail": "no order 'ord_x' in your workspace"}` |
| `400` | Invalid combination the UI should not send | release-gate without `order.payment`, bad `status`, no workspace on the account |
| `409` | Email or `merchant_key` already taken | `{"detail": "merchant key 'default' is already in use"}` |
| `422` | Pydantic validation (short password, unknown enum, bad limit) | FastAPI's `detail` array |

`400` on the sandbox test with no payment deliberately mirrors the bot contract
in `src/p2p/router.py`, so the wizard teaches the real rule.

---

## 4. Conventions worth knowing before you render

- **`risk_score` / `confidence` / `behavioural_score` are floats 0–1.** Format as
  `93%`; do not rescale to 0–100.
- **Timestamps are ISO-8601 with an explicit offset** (`"2026-09-25T20:08:02Z"`).
  The ledger stores naive UTC; the API re-attaches `Z` so a client can never
  guess wrong. Render in IST, offer UTC in a tooltip.
- **Money is a number, never formatted.** `inr_value`, `price_inr`, `amount` are
  INR; `cost_usd` / `spend_usd` / `vendor_spend_usd` are USD.
- **`account_no_masked` is the last four digits only.** There is no full account
  number anywhere in the API, the evidence bundle, or the database.
- **`verdict` is `ALLOW` / `HOLD` / `BLOCK`; `action` is `release` / `hold` /
  `reject`.** Both are always present — render the verdict, act on the action.
- **`degraded: true` means a required vendor was unreachable** and the guard
  refused to auto-allow. It is a first-class state, not an error row.
- **Paging** returns `{items, total, limit, offset, has_more}`. `has_more` is
  authoritative; do not infer from `items.length`.
- **Filters are URL-persistable by design** — every ledger filter is a query
  param, so a view can be pasted into a bank email.

---

## 5. Endpoint reference

### Auth & workspaces

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/signup` | Create account + first workspace, returns a token |
| `POST` | `/api/v1/auth/login` | Email + password → token |
| `GET` | `/api/v1/auth/me` | Current user + workspaces (with order counts) |
| `POST` | `/api/v1/auth/merchants` | Add another workspace to the same login |

```json
POST /api/v1/auth/signup
{"email":"Ramesh@example.com","password":"…min 12 chars…","business_name":"Ramesh Desk","merchant_key":"desk_one"}

201 →
{"access_token":"eyJhbG…","token_type":"bearer","expires_in":86400,
 "user":{"user_id":1,"email":"ramesh@example.com","name":null},
 "merchants":[{"merchant_key":"desk_one","business_name":"Ramesh Desk","role":"owner","country":"IN","orders":0}]}
```

`merchant_key` is what your bot must send as `order.merchant_id`. If you already
run a bot, pass its existing value at signup and the history it writes is yours
immediately.

### Connection wizard

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/integration/status?merchant=default` | Connected yet? endpoints, topics, signature help |
| `GET` | `/api/v1/integration/keys?merchant=default` | Key list — **never** includes a secret |
| `POST` | `/api/v1/integration/keys?merchant=default` | Mint a key; `hmac_secret` is returned once |
| `DELETE` | `/api/v1/integration/keys/{key_id}` | Revoke (row kept, `active: false`) |
| `POST` | `/api/v1/integration/test` | Run one real decision, nothing persisted |

```json
GET /api/v1/integration/status?merchant=default →
{"merchant_key":"default","transport":"rest","connected":true,"has_api_key":true,
 "hmac_enforced":false,"orders_total":24,
 "first_order_at":"2026-09-25T20:07:44Z","last_order_at":"2026-09-25T20:08:03Z",
 "endpoints":[{"method":"POST","path":"/api/v1/p2p/orders/pre-screen","purpose":"screen the buyer before INR is accepted"}, …],
 "kafka_topics":["sentinel.p2p.order","sentinel.p2p.decision"],
 "signature_help":"X-Sentinel-Signature = hex(hmac_sha256(secret, \"{timestamp}.\" + raw_body)); X-Sentinel-Timestamp = unix seconds, 300s tolerance. Sign the bytes you send, not a re-serialised object.",
 "sandbox_available":true}
```

`connected` means a *persisted* order exists — a sandbox test never flips it,
because "I clicked test" is not "my bot is live".

```json
POST /api/v1/integration/test
{"phase":"release_gate","order":{"order_id":"ord_probe","merchant_id":"default","qty":10,"price_inr":905,
  "buyer":{"binance_user":"u_x","verified_name":"Test Buyer","trade_count":5,"account_age_days":200},
  "payment":{"method":"upi","payer_name_on_account":"Someone Else","amount":9050,"utr":"99","confirmed":true}}}

200 →
{"decision":{"order_id":"ord_probe","phase":"release_gate","verdict":"BLOCK","action":"reject",
  "risk_score":0.9,"confidence":0.9,
  "reasons":["Third-party payment (name mismatch) at release gate","third_party_payment: name-match risk 0.90"],
  "hard_rules":[],"step_up":[],"evidence_ref":"EV-…","degraded":false,"decided_at":"…"},
 "persisted":false,"published":false}
```

### Ledger

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/portal/orders` | The history table. Filters below |
| `GET` | `/api/v1/portal/orders/export` | Same filters, streams CSV (`text/csv`, attachment) |
| `GET` | `/api/v1/portal/orders/{order_id}` | Full detail: decision, buyer, payment, wallet, sources, pack, voucher, register, overrides, timeline |
| `GET` | `/api/v1/portal/orders/{order_id}/evidence?fmt=markdown\|json` | The pack as a file download |
| `POST` | `/api/v1/portal/orders/{order_id}/override` | `{action, reason(min 10 chars)}`, append-only |
| `GET` | `/api/v1/portal/holds` | `verdict=HOLD`, oldest first (or `sort=inr_value`) |

`/orders` query parameters: `merchant`, `verdict` (repeatable), `phase`
(repeatable), `risk_min`, `risk_max`, `hard_rule`, `degraded`, `has_utr`,
`payment_method`, `pool`, `confirmed`, `buyer_key`, `search`, `since`, `until`,
`sort` (`decided_at` · `created_at` · `risk_score` · `confidence` · `inr_value` ·
`verdict`), `desc`, `limit` (≤200), `offset`. Unknown `sort` values fall back to
`decided_at`; nothing user-supplied reaches `ORDER BY` as raw SQL.

```json
GET /api/v1/portal/orders?limit=1&verdict=BLOCK →
{"items":[{"order_id":"ord_00012","merchant_id":"default","decided_at":"2026-09-25T20:04:50.479589Z",
  "created_at":"2026-09-25T20:04:50Z","phase":"release_gate","asset":"USDT","fiat":"INR",
  "qty":25.0,"price_inr":900.0,"inr_value":22500.0,
  "buyer_user":"u_amesh","buyer_name":"Ramesh Kumar","buyer_country":"IN",
  "verdict":"BLOCK","action":"reject","risk_score":0.95,"confidence":0.95,
  "hard_rules":["wallet_exposure"],
  "reasons":["Hard rule triggered: wallet_exposure","wallet_exposure: wallet exposure 0.95",
             "structuring: 4 credits totalling INR 270377"],
  "degraded":false,"evidence_ref":"EV-EB83DFE4EA6F",
  "voucher_ref":null,"pool":null,"voucher_status":null,
  "utr":"420000000012","payer_name":"Ramesh Kumar","account_no_masked":"6655","payment_method":"upi",
  "spend_usd":0.3073,"latency_ms":1180,"rules_total":3}],
 "total":4,"limit":1,"offset":0,"has_more":true}
```

Order detail (abridged to the shape, real keys):

```json
GET /api/v1/portal/orders/ord_00002 →
{"order":{…as above…},
 "decision":{"verdict":"ALLOW","action":"release","risk_score":0.05,"confidence":0.95,
   "hard_rules":[],"reasons":[…],"evidence":[…],"step_up":[],
   "behavioural_score":0.0,"vendor_max_risk":0.05,"composite":0.05,"degraded":false,"decided_at":"…"},
 "buyer":{"binance_user":"u_vikram","verified_name":"Vikram Shah","country":"IN",
   "trade_count":22,"completion_rate":0.98,"account_age_days":140,
   "chat_snippet":null,"chat_red_flags":[],"risk_flags":[]},
 "payment":{"method":"upi","utr":"420000000002","vpa":"u_vikram@okaxis","account_no_masked":"4028",
   "ifsc":"HDFC0001234","bank_name":null,"payer_name_on_account":"Vikram Shah",
   "amount":69952.0948,"credit_ts":null,"confirmed":true},
 "wallet":null,
 "vendor_calls":[{"provider":"sanctions_local","category":"sanctions","status":"ok","risk":0.0,
   "detail":"","matched_list":"","raw_ref":"","cost_usd":0.0,"latency_ms":410}, …],
 "evidence":{"reference":"EV-1E09FFB5E968","phase":"release_gate","verdict":"ALLOW",
   "created_at":"2026-09-25T20:08:02Z","formats":["markdown","json"],
   "download_path":"/api/v1/portal/orders/ord_00002/evidence"},
 "voucher":{"voucher_ref":"VCH-5987E3E5B9","order_id":"ord_00002","virtual_account":"VA497219864323",
   "vpa":"sentinel+_00002@okhdfcbank","utr":null,"amount":69952.09,"pool":"quarantine",
   "status":"issued","credited_at":null,"sweep_after":"2026-09-27T20:08:02.883977Z",
   "alerts":["credit for order ord_00002 has no UTR to trace"]},
 "compliance":[{"event_type":"TDS_194S","order_id":"…","amount":…,"created_at":"…","payload":{…}}, …],
 "overrides":[],
 "timeline":[{"name":"order_created","at":"…","detail":""},
   {"name":"guard_pre_screen","at":"…","detail":"ALLOW (release) risk 0.05"},
   {"name":"guard_release_gate","at":"…","detail":"ALLOW (release) risk 0.05"},
   {"name":"voucher_issued","at":"…","detail":"VCH-5987E3E5B9 pool=quarantine"},
   {"name":"vendor_fanout","at":"…","detail":"3 calls, max 410 ms"},
   {"name":"evidence_stored","at":"…","detail":"EV-1E09FFB5E968 immutable"}],
 "not_screened":false}
```

Read these fields the way the engine means them:

- `vendor_calls` and `compliance` are **scoped to the gate of the row you opened**.
  An order screened at both gates has two sets; conflating them doubles apparent
  spend.
- `decision.vendor_max_risk`, `behavioural_score` and `composite` let you draw the
  score build-up (`0.5·vendor + 0.5·behavioural`, floored at `vendor_max`) instead
  of showing a bare number.
- `timeline` emits one node per gate, so the two-gate story is visible by default.
- `chat_snippet` is `null` by design: the evidence bundle is PII-light and does
  not store chat text. `chat_red_flags` is derived from the stored reason string
  and is the field to render.
- `bank_name`, `credit_ts` come from the pack only when the bot supplied them.
- `wallet` is present when the order carried addresses (stored in the pack since
  this release; older bundles have `null`).
- `not_screened` is reserved for a future "orders I had before Sentinel" view and
  is always `false` today.

### Buyers, settlement, freezes, compliance register

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/portal/counterparties` | `search`, `flagged_only`, `since`, `until`, `sort` (`seen` · `flagged` · `inr_traded` · `last_seen_at` · `peak_risk`), `limit`, `offset` |
| `GET` | `/api/v1/portal/counterparties/{buyer_key}` | That buyer's orders (paged `OrderRow`) |
| `GET` | `/api/v1/portal/vouchers` | `pool`, `status`, `since`, `until`; `alerts` recomputed on read |
| `GET` | `/api/v1/portal/liens` | `status` filter; `evidence_available` joins the vault |
| `POST` | `/api/v1/portal/liens` | `{order_id?, utr?, account_no_masked?, source, notice_text}` → `{case, assembled, evidence_markdown, missing}` |
| `PATCH` | `/api/v1/portal/liens/{case_ref}` | `{status, note?}`; `note` is appended to `notice_text` with a UTC stamp |

```json
GET /api/v1/portal/counterparties →
{"items":[{"buyer_key":"u_priya","binance_user":"u_priya","verified_name":"Priya Nair",
  "seen":6,"flagged":0,"clean_streak":6,"allow":6,"hold":0,"block":0,
  "inr_traded":418800.5,"inr_blocked":0.0,"last_risk":0.05,"last_verdict":"ALLOW",
  "last_seen_at":"2026-09-25T20:08:01Z","first_seen_at":"2026-09-25T20:07:44Z","watch":false}, …],
 "total":5,"limit":50,"offset":0,"has_more":false}
```

`seen / allow / hold / block / inr_*` are computed from **your** orders.
`clean_streak`, `last_verdict` and `last_risk` come from the engine's
`counterparties` row, which is keyed by buyer globally — it is shown, not
rewritten, because it is the exact value the rules read. `watch` is a portal-side
display flag and is not persisted yet.

A freeze case with no matching pack says so instead of inventing one:

```json
POST /api/v1/portal/liens {"utr":"9999999999"} → 201
{"case":{"case_ref":"LIEN-…","merchant_id":"default","status":"open","evidence_available":false, …},
 "assembled":false,
 "evidence_markdown":null,
 "missing":["No stored evidence pack for this order. Either it predates your Sentinel connection or the gate was never called for it."]}
```

### Aggregates

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/v1/portal/overview?window=today\|24h\|7d\|30d\|all` | `OverviewResponse` — the whole dashboard in one snapshot |
| `GET` | `/api/v1/portal/insights?window=…` | same shape (rules, providers, cost, mix) |
| `GET` | `/api/v1/portal/stats/summary?window=…` | `StatsSummary` — just the KPI strip |

`/overview` and `/insights` are the same payload: the ledger slice is read once
and reused for every chart, so the cards cannot disagree with each other. Use
`/stats/summary` when you only need the strip.

```json
GET /api/v1/portal/stats/summary?window=7d →
{"merchant_keys":["default"],"window":"7d","orders":24,
 "verdicts":{"allow":19,"hold":1,"block":4,"degraded":0},
 "inr_blocked":144910.0,"inr_released":821703.89,"inr_on_hold":7224.0,
 "auto_cleared_pct":79.17,"median_latency_ms":930.0,"p95_latency_ms":1180.0,
 "vendor_spend_usd":7.3747,"spend_per_order_usd":0.307279,
 "holds_open":1,"holds_overdue":0,
 "quarantine_inr":450863.96,"awaiting_sweep_inr":414463.96,"unmatched_credits":2,
 "lien_cases_open":1}
```

`OverviewResponse` adds:

| Field | Shape | Use |
|---|---|---|
| `mix` | `{allow,hold,block,degraded}` | verdict split bar |
| `mix_by_phase` | `{"pre_screen": {...}, "release_gate": {...}}` | the phase toggle |
| `risk_histogram` | 20 buckets `{low,high,count}` over 0–1 | draw threshold rules at 0.50 / 0.80 |
| `timeseries` | `[{bucket,allow,hold,block,inr_blocked,decisions}]` | bucket-aligned; gaps are real zeros |
| `top_rules` | `[{name,triggers,led_to_block}]` | rule leaderboard |
| `providers` | `[{provider,category,calls,ok,errored,unavailable,skipped,p50_latency_ms,p95_latency_ms,cost_usd,status}]` | signal health; `status` is `ok` · `degraded` · `down` |
| `needs_action` | `[OrderRow]` | the HOLD queue, oldest first |
| `sparklines` | `{orders, blocked, inr_blocked, latency}` each `{values: 7 floats}` | oldest → newest, today last |
| `summary` | `StatsSummary` | KPI strip |

`holds_overdue` counts HOLDs older than 15 minutes — the Binance P2P release
window — so "needs you" can be red without the client computing it.

Chart data notes: `bucket` timestamps are epoch-aligned, so the x-axis never
shifts because the first decision landed at :07. Percentiles are nearest-rank
over per-decision worst vendor call. Aggregates read at most 20,000 ledger rows
(newest first) — beyond that the charts describe the recent slice, which is the
practical ceiling for a merchant desk.

### Live feed

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/portal/feed` | Server-Sent Events, `text/event-stream` |

Query: `merchant`, `after_id`, `poll_seconds` (0.2–30), `max_events` (0 =
unbounded), `once`.

```
GET /api/v1/portal/feed?after_id=0&once=true
data: {"id":41,"order_id":"ord_00001","merchant_id":"default","phase":"pre_screen","verdict":"ALLOW","action":"release","risk_score":0.05,"confidence":0.95,"inr_value":69952.09,"asset":"USDT","qty":77.3,"buyer_user":"u_vikram","buyer_name":"Vikram Shah","utr":null,"hard_rules":[],"reasons":[],"degraded":false,"evidence_ref":"EV-…","decided_at":"2026-09-25T20:07:44.771200+00:00"}

: ping
```

- **Cursor semantics:** omit `after_id` → start at the newest (a fresh tab does
  not re-read history); `after_id=0` → replay the backlog; `after_id=<id>` →
  resume. The cursor is the row primary key, not a timestamp, because both gates
  can decide in the same millisecond and a ledger that skips or repeats a verdict
  is worse than one that polls often.
- Events are emitted **oldest first** so your client can store the last `id` and
  resume exactly.
- Heartbeat is an SSE comment line (`: ping`) — it will not show up as a message.
- `once=true` is the documented fallback for proxies that buffer event streams,
  and it is also what makes the feed testable in one request. A frontend should
  treat a failed `EventSource` as a signal to poll `/orders` instead.

---

## 6. What is deliberately not here yet

So mockups do not promise a screen the API cannot fill:

| Screen element | Status |
|---|---|
| Evidence pack as **PDF** | Not built. `formats` is `["markdown","json"]`; add a `fmt=pdf` branch in `evidence.py` + `data_router.py` when needed |
| **Sweep now** on a voucher | Read-only. Pool/status writes need a settlement action endpoint |
| **Buyer `watch`** toggle | Field exists, always `false`; not persisted |
| **Statement upload** on a HOLD | Not built — no attachments table yet |
| **Re-screen now** button | Works today via `POST /api/v1/integration/test` (returns a fresh verdict, persists nothing); a portal-native "re-screen and record it" endpoint is still open |
| **Notification routing**, **billing**, **team invites**, **IP allowlist** | No endpoints |
| **Per-merchant policy overrides** (BLOCK/HOLD thresholds) | Hardcoded in `fusion.py`; the simulator is read-only by design until a policy store exists |
| **Orders from before your connection** | `not_screened` is reserved and unused |
| **Cross-merchant aggregates** for the landing page ticker | Not built; today's public numbers must stay illustrative |

---

## 7. Testing notes

- Portal tests live in `tests/test_portal/` and use `httpx.AsyncClient` over an
  ASGI transport, so the app, the SQLite engine and the test body share one event
  loop. The root `conftest.client` fixture is not used there: it assigns the
  `test_engine` *fixture function* to `src.shared.db.engine`, so anything that
  really touched the database through it failed.
- `pytest --cov` is in `pyproject.toml`'s `addopts`; if `pytest-cov` is missing,
  override with `-o addopts=""`.
- Environment note: this repo's `.venv` was missing packages that
  `requirements.txt` already declares — `asyncpg`, `greenlet`, `alembic`,
  `uvicorn`, `pytest-cov` were installed to run and test the portal at all.
