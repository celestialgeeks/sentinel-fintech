# Sentinel — Pre-Settlement AML & Fraud Guard for Crypto P2P Merchants

> A production-grade risk brain that screens a Binance P2P payment for illicit
> funds **before** the merchant accepts the credit or releases crypto — and
> blocks the deal when the money looks dirty.

---

## The problem

A P2P merchant sells USDT for rupees: a buyer transfers INR to the merchant's
bank account, and once the payment is verified the merchant releases USDT from
escrow. The danger is not the crypto — it is the **INR credit**.

If the buyer is paying with proceeds of crime (a mule account, cyber-fraud
victim money, or an account already under a police / ED investigation), then
when authorities trace the victim's funds, the freeze follows the money into
**the merchant's own account**. Under India's PMLA framework and the National
Cyber Crime (Cyber-TAT / N4C) freeze process, an account that received tainted
money can be lien-marked or frozen — even if the merchant never released the
crypto and was never a party to the crime.

By the time a screenshot of a "successful" payment is visible, the money is
already in transit. Manual review is too slow for 15-minute P2P release windows.

## What Sentinel does

Sentinel sits alongside the merchant's existing trading automation and makes one
decision, fast: **is this counterparty and this incoming payment clean enough to
accept the credit and release the crypto?**

It answers with `ALLOW` / `HOLD` / `BLOCK` plus a confidence score, the reasons,
the vendor evidence behind them, and a reference to a stored evidence pack.

Two gates wrap the lifecycle of every order:

| Gate | When | Question |
|------|------|----------|
| **Pre-screen** | order created / buyer claims paid, **before** INR is accepted | Should we let this buyer pay at all? |
| **Release gate** | bank credit confirmed, **before** USDT leaves escrow | Is the confirmed credit genuine and same-person? |

The design principle: **the freeze reaches the merchant through the credit's
fund-trail, so screen before the money settles — not only before release.**

---

## How it works

```
Binance P2P bot (executor)
   |  order + confirmed-credit events                ^ signed release / hold / reject
   v                                                 |
[Guard API or Kafka: sentinel.p2p.order]
   v
Vendor fan-out (resilient, cached, circuit-broken, tiered, fail-closed)
   • On-chain wallet exposure   Chainalysis / Elliptic / CryptoAuthet
   • India mule / bank / name    IDfy / Signzy / HyperVerge
   • Sanctions / PEP             live feed + local watchlist
   • Consented bank credit       Account Aggregator (Setu / SAHAMATI)
   v
Signal fusion  = vendor verdicts + behavioural rules (velocity, structuring,
                 freshness, repeat-counterparty trust, third-party / name mismatch)
   v
ALLOW / HOLD / BLOCK  ->  settlement voucher + evidence pack + compliance log
```

Key safety properties:

- **Third-party payment is disqualifying.** A payer name on the bank credit that
  does not match the buyer's Binance-verified name is a `BLOCK` at the release
  gate — this mirrors Binance's own appeal rule and is the single most common
  cause of merchant account freezes.
- **Hard blocks** for sanctions matches, confirmed mule accounts, and severe
  on-chain exposure.
- **Fail-closed.** If a required vendor is unreachable, the guard never silently
  allows — it degrades to `HOLD`.
- **Evidence-first.** Every decision writes a per-order evidence bundle that can
  be exported as markdown/JSON — what actually gets an account unfrozen.

---

## Tech stack

| Layer | Technology |
|---|---|
| API & orchestration | FastAPI + Uvicorn (async) |
| Data store | PostgreSQL (SQLAlchemy 2.0 async) + Alembic |
| Cache / fast state | Redis (velocity, trust, vendor-result cache) |
| Vector & graph | Milvus (fuzzy entity match) + Neo4j (money-trail) |
| Streaming | Apache Kafka (order + decision events) |
| ML / LLM | scikit-learn / XGBoost + LangChain (entity resolution, KYB/RAG) |
| Risk data | Chainalysis, Elliptic, CryptoAuthet, IDfy, Signzy, HyperVerge, Account Aggregator |
| Containerisation | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |
| Testing | pytest (+ pytest-asyncio), Locust |

---

## Project layout

```
src/
├── p2p/            # the guard: rules, fusion, pipeline, orchestrator
│   ├── fusion.py        # ALLOW/HOLD/BLOCK policy
│   ├── rules.py         # P2P risk signals
│   ├── state.py         # durable velocity / counterparty trust (Redis)
│   ├── pipeline.py      # one code path for REST + Kafka
│   ├── consumer.py      # idempotent sentinel.p2p.order orchestrator
│   ├── evidence.py      # per-order evidence pack + export
│   ├── settlement.py    # quarantine vouchers + misroute alerts
│   ├── compliance.py    # STR-context + 194S TDS capture (advisory)
│   ├── lien.py          # freeze-notice intake -> evidence case
│   ├── store.py         # best-effort persistence
│   └── router.py        # /api/v1/p2p/* endpoints
├── vendors/        # pluggable data-source adapters (+ mocks, resilience, aggregator)
├── gateway/        # ingestion + Neo4j money-trail engine
├── screening/      # AML rules, watchlists, entity resolution
├── fraud/          # behavioural + ML scoring, alert triage
├── verification/   # step-up verification pipeline
├── decision/       # multi-signal decision engine
├── merchant/       # KYB / RAG document extraction, risk scoring
├── api/            # FastAPI app, middleware (auth, rate-limit, HMAC), routers
└── shared/         # db, models, cache, kafka, graph_db, vector_db
```

---

## Quick start

Prerequisites: Docker Desktop (v24+) with Compose, Python 3.11+, Git.

```bash
git clone https://github.com/celestialgeeks/sentinel-fintech.git
cd sentinel-fintech
cp .env.example .env          # optionally add vendor keys
docker compose up -d
docker compose exec api python -m src.scripts.migrate upgrade
curl http://localhost:8000/health
```

The guard runs out of the box with deterministic mock providers (no vendor
contracts needed). Add real keys to `.env` to swap them for live data — the
provider registry switches automatically. Set `USE_MOCKS_WHEN_UNCONFIGURED=false`
in production so a missing required provider degrades to `HOLD`.

### Calling the gates

```bash
# 1) Pre-screen before accepting payment
curl -X POST http://localhost:8000/api/v1/p2p/orders/pre-screen \
  -H 'Content-Type: application/json' -d '{"order": {...}, "phase": "pre_screen"}'

# 2) Release-gate before releasing USDT (requires the confirmed credit in order.payment)
curl -X POST http://localhost:8000/api/v1/p2p/orders/release-gate \
  -H 'Content-Type: application/json' -d '{"order": {...}, "phase": "release_gate"}'
```

When `GUARD_HMAC_SECRET` is set, the bot authenticates calls with:

```
X-Sentinel-Timestamp: <unix seconds>
X-Sentinel-Signature: hex(hmac_sha256(secret, f"{timestamp}." + raw_body))
```

### API summary

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/p2p/orders/pre-screen` | Screen a buyer before accepting payment |
| `POST` | `/api/v1/p2p/orders/release-gate` | Gate the escrow release on the confirmed credit |
| `GET`  | `/api/v1/p2p/orders/{id}/evidence` | Export the order's evidence pack (`?fmt=json`) |
| `POST` | `/api/v1/p2p/liens` | Report a freeze notice and assemble its case |
| `GET`  | `/api/v1/p2p/health` | Guard health check |
| `GET`  | `/health` | Service health check |

Docs at `/docs` (OpenAPI), metrics at `/metrics`.

---

## Testing

```bash
docker compose run --rm api pytest tests/ -v
```

The guard ships with unit + integration tests (fusion policy, P2P rules,
vendor-aggregator fail-closed behaviour, both REST gates, HMAC, and the
idempotent Kafka consumer path) under `tests/test_p2p/`.

---

## Compliance note

Sentinel is a risk-screening and evidence tool, not legal or tax advice. Large
P2P volumes can themselves constitute Virtual Digital Asset Service Provider
(VASP) activity requiring FIU-IND registration under the PMLA, and VDA transfers
may attract 1% TDS under section 194S. The compliance module only *captures*
context for a qualified professional; obtain legal and tax advice for your
jurisdiction and volumes. Screening materially reduces account-freeze risk but
cannot eliminate it — no system removes the residual risk of holding funds that
authorities later trace.

---

## Architecture documents

- [docs/REALTIME_ARCHITECTURE.md](docs/REALTIME_ARCHITECTURE.md) — event pipeline design
- [docs/IMPLEMENTATION_PLAN_REALTIME.md](docs/IMPLEMENTATION_PLAN_REALTIME.md) — phased build plan
- [docs/RESEARCH_REPORT.md](docs/RESEARCH_REPORT.md) — research background

## Academic lineage

Sentinel began as a B.Tech Major Project (IPS Academy, Indore — RGPV, CSE-AIML),
and the codebase retains the AML / fraud / merchant-onboarding research engines
that informed the guard. Its present form is a working product for real P2P
merchants.

## License

Academic project — IPS Academy, Indore.
