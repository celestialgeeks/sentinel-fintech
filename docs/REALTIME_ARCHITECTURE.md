# Sentinel — Real-Time Payment Screening Architecture

> Pivot from batch file-upload to real-time webhook-based payment screening with money trail analysis and AI agent verification.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CUSTOMER CRM LAYER                                  │
│  (Stripe · Plaid · your own CRM) — payments originate here                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Webhook (HTTPS POST)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SENTINEL — REAL-TIME GATEWAY                            │
│                                                                              │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐    │
│  │  Webhook Ingest  │──▶│ Money Trail      │──▶│ Agent Verification   │    │
│  │  (Stripe/Plaid)  │   │ Engine (Neo4j)   │   │ (Ask · Gather ·      │    │
│  │                  │   │                  │   │  Verify · Decide)     │    │
│  └──────────────────┘   └──────────────────┘   └──────────────────────┘    │
│         │                       │                        │                  │
│         ▼                       ▼                        ▼                  │
│  Kafka: sentinel.payment   Kafka: sentinel.trail      Kafka: sentinel.decision│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BANKING / BLOCKCHAIN LAYER                             │
│              (Approve / Review / Block decision flows through)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Payment arrives
    │
    ▼
1. INGEST — Parse webhook (Stripe: payment_intent.succeeded, Plaid: transaction)
   → Normalize to PaymentEvent
   → Publish to Kafka topic 'sentinel.payment'
    │
    ▼
2. TRAIL — Follow money through Neo4j graph
   → find_fraud_rings(seed_entity, depth=5)
   → detect_circular_flow()
   → detect_structuring()
   → get_counterparty_risk()
   → Build TrailContext
    │
    ▼
3. SCREEN — AML watchlist check (existing ScreeningEngine)
   → OFAC/UN/EU sanctions
   → High-risk jurisdiction flags
    │
    ▼
4. VERIFY — AI agent asks questions, gathers context
   → Generate targeted questions (gaps in trail + screening)
   → Resolve: CRM lookups, entity resolution, knowledge base
   → Agentic reasoning: LLM evaluates all signals
    │
    ▼
5. DECIDE — Final decision
   → Rule-based: thresholds on risk score
   → Agentic: LLM final judgment with evidence
   → Hybrid: rules first, agent for edge cases
   → Output: APPROVE / REVIEW / BLOCK + confidence + explanation
```

## Components

### 1. Gateway (`src/gateway/`)
- **router.py** — FastAPI endpoints for payment ingestion and trail queries
- **ingestion.py** — Webhook parser, normalizer, Kafka publisher
- **trail.py** — Money trail analysis engine (Neo4j + rules)
- **schemas.py** — PaymentEvent, MoneyTrailNode, TrailAnalysis, TrailFlags
- **crm_connectors.py** — StripeConnector, PlaidConnector interfaces

### 2. Verification (`src/verification/`)
- **pipeline.py** — 4-phase VerificationPipeline (gather → question → verify → decide)
- **strategies.py** — RuleBased, Agentic, Hybrid decision strategies
- **schemas.py** — VerificationQuestion, VerificationAnswer, VerificationContext, VerificationDecision
- **router.py** — FastAPI endpoints for verification runs

### 3. Decision (`src/decision/`)
- **engine.py** — DecisionEngine: aggregate risk, enforce policy, collect evidence
- **router.py** — FastAPI endpoints for decision runs
- **Policy** — Configurable thresholds: BLOCK (0.8), REVIEW (0.5)

### 4. Kafka Pipeline (`src/kafka/`)
- **consumer.py** — Orchestrates: payment → trail → screen → verify → decision
- Publishes to `sentinel.payment`, `sentinel.trail`, `sentinel.decision`

### 5. Cache (`src/cache/`)
- **trail_cache.py** — Redis TTL cache for trail analysis (5 min)

## Technology Choices

| Layer | Technology | Reason |
|-------|-----------|--------|
| API | FastAPI + Uvicorn | Async, auto-docs, existing |
| Events | Apache Kafka | Event-driven, decoupled, replayable |
| Graph | Neo4j | Money trail = natural graph problem |
| Vector | Milvus | Entity resolution, fuzzy matching |
| Cache | Redis | Fast lookups, rate limiting, TTL cache |
| DB | PostgreSQL | ACID transactions, JSONB for flexibility |
| LLM | OmniRoute (openrouter) | Multi-model, free tier, fallback-ready |

## API Endpoints

```
POST /api/v1/gateway/payment          — Ingest payment webhook
POST /api/v1/gateway/trail/{id}        — Analyze money trail
GET  /api/v1/gateway/trail/{id}/status — Trail analysis status
GET  /api/v1/gateway/health            — Health check

POST /api/v1/verification/run          — Run full verification
POST /api/v1/verification/question/{id} — Ask specific question
GET  /api/v1/verification/status/{id}   — Verification status
GET  /api/v1/verification/decision/{id} — Final decision

POST /api/v1/decision/run              — Run decision engine
GET  /api/v1/decision/health           — Decision health check
```

## Phase Plan

See `IMPLEMENTATION_PLAN_REALTIME.md` for detailed per-phase breakdown.
