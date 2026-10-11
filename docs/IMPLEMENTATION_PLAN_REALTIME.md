# Sentinel — Real-Time Implementation Plan

> Phased roadmap for pivoting from batch file-upload screening to real-time webhook-based payment screening with money trail analysis and AI agent verification.

---

## Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE

**Goal:** Gateway layer with webhook ingestion and Kafka backbone.

### Files Created
- `src/gateway/__init__.py`
- `src/gateway/schemas.py` — PaymentEvent, MoneyTrailNode, TrailAnalysis, TrailFlags, AgentContext
- `src/gateway/crm_connectors.py` — BaseCRMConnector, StripeConnector, PlaidConnector
- `src/gateway/ingestion.py` — PaymentWebhookIngestor
- `src/gateway/router.py` — FastAPI router

### Acceptance Criteria Met
- [x] `POST /api/v1/gateway/payment` accepts Stripe/Plaid webhook payloads
- [x] Normalized PaymentEvent published to Kafka topic `sentinel.payment`
- [x] Health check `GET /api/v1/gateway/health` returns 200
- [x] All schemas pass Pydantic validation
- [x] CRM connectors are abstract base + 2 concrete implementations

---

## Phase 2: Money Trail Engine (Weeks 3-4) ✅ COMPLETE

**Goal:** Graph-based trail analysis with circular flow and structuring detection.

### Files Created
- `src/gateway/trail.py` — MoneyTrailEngine class
- `src/cache/trail_cache.py` — Redis TTL cache for trail results
- Extended `src/gateway/router.py` — added `/trail/{id}` endpoint

### MoneyTrailEngine Methods
- `follow_trail(payment_id, depth=5)` — Neo4j graph traversal
- `detect_circular_flow(payment_id)` — detect money looping back
- `detect_structuring(payment_id)` — detect split transactions below thresholds
- `get_counterparty_risk(entity_id)` — check entity risk from PG + Neo4j
- `build_trail_context(payment_id)` — assemble full context for verification

### Acceptance Criteria Met
- [x] Trail follows up to 5 hops in Neo4j graph
- [x] Circular flow detection works (A→B→C→A pattern)
- [x] Structuring detection flags transactions < threshold from same sender
- [x] Trail analysis published to Kafka topic `sentinel.trail`
- [x] Trail context includes: nodes, flags, aggregated risk score
- [x] Redis cache with 5-min TTL for trail results

---

## Phase 3: Agent Verification (Weeks 5-6) ✅ COMPLETE

**Goal:** AI agent asks questions, gathers context, verifies, then decides.

### Files Created
- `src/verification/__init__.py`
- `src/verification/schemas.py` — VerificationQuestion, VerificationAnswer, VerificationContext, VerificationDecision
- `src/verification/strategies.py` — DecisionStrategy, RuleBasedStrategy, AgenticStrategy, HybridStrategy
- `src/verification/pipeline.py` — VerificationPipeline (4-phase flow)
- `src/verification/router.py` — FastAPI router

### VerificationPipeline Flow
1. **Gather** — collect trail context, screening flags, fraud scores
2. **Question** — generate targeted questions based on gaps
3. **Verify** — resolve questions via CRM connectors, knowledge base, entity resolution
4. **Decide** — aggregate signals, produce final decision with confidence

### Acceptance Criteria Met
- [x] Pipeline runs end-to-end: gather → question → verify → decide
- [x] 3 decision strategies: rule-based, agentic, hybrid
- [x] Questions generated based on missing context, not random
- [x] Answers resolved from CRM/DB/knowledge base
- [x] Final decision includes: APPROVE/REVIEW/BLOCK + confidence + reasoning

---

## Phase 4: Decision Pipeline (Weeks 7-8) ✅ COMPLETE

**Goal:** Aggregate all signals, enforce policy, ship decisions.

### Files Created
- `src/decision/__init__.py`
- `src/decision/engine.py` — DecisionEngine (policy enforcement)
- `src/decision/router.py` — FastAPI router for decision endpoints
- `src/kafka/consumer.py` — Kafka consumer orchestrating full pipeline
- Updated `src/api/main.py` — wire all routers and consumer

### DecisionEngine Logic
- Combine: trail risk (35%) + screening risk (25%) + verification confidence (15%) + policy flags (25%)
- Apply policy rules (block if >0.8, review if >0.5, approve if <0.5)
- Log decision with full evidence trail
- Publish decision to Kafka topic `sentinel.decision`

### Acceptance Criteria Met
- [x] Decision aggregates all signal sources
- [x] Policy enforcement is configurable (thresholds in DecisionPolicy)
- [x] Full evidence trail logged for audit
- [x] Decision published to Kafka
- [x] All routes wired into FastAPI main.py
- [x] Kafka consumer connects payment → trail → screen → verify → decision

---

## Kafka Event Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Kafka Topic Topology                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  sentinel.payment    ←── Webhook Ingestor (POST /gateway/payment)    │
│       │                                                              │
│       ▼                                                              │
│  [Kafka Consumer: src/kafka/consumer.py]                             │
│       │                                                              │
│       ├──▶ sentinel.trail    ←── MoneyTrailEngine (Neo4j)            │
│       │                                                              │
│       ├──▶ [ScreeningEngine] (sync, in-process)                     │
│       │                                                              │
│       ├──▶ sentinel.verification ←── VerificationPipeline            │
│       │                                                              │
│       └──▶ sentinel.decision ←── DecisionEngine (policy enforcement) │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Migration Path

### Current (Batch File Upload)
```
POST /api/v1/screening/transactions
  → ScreeningEngine.screen(txn)
  → Returns ScreeningResponse (APPROVE/REVIEW/BLOCK)
```

### New (Real-Time Webhooks)
```
POST /api/v1/gateway/payment
  → PaymentWebhookIngestor.ingest(payload)
  → Kafka: sentinel.payment
     ↓
  [Kafka Consumer]
     ├──▶ MoneyTrailEngine.follow_trail() → Kafka: sentinel.trail
     ├──▶ ScreeningEngine.screen() (sync)
     └──▶ VerificationPipeline.run() → Kafka: sentinel.decision
          → DecisionEngine.decide() → APPROVE/REVIEW/BLOCK
```

### Backward Compatibility
- Existing screening endpoints remain functional
- New gateway/verification/decision endpoints are additive
- Kafka topics are separate (no interference)
- Batch mode can coexist with real-time mode during transition

---

## Tech Stack (Confirmed)

| Component | Technology | Status |
|-----------|-----------|--------|
| API Framework | FastAPI | ✓ |
| Event Streaming | Apache Kafka | ✓ (producer/consumer) |
| Graph DB | Neo4j | ✓ (client + queries) |
| Vector DB | Milvus | ✓ (client) |
| Cache | Redis | ✓ |
| Primary DB | PostgreSQL | ✓ |
| ORM | SQLAlchemy | ✓ |
| LLM Router | OmniRoute | ✓ (openrouter via proxy) |
| Testing | pytest | ✓ |

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| Kafka unavailable at startup | Graceful fallback: process synchronously |
| Neo4j slow for deep trails | Cache trail results in Redis (TTL 5min) |
| LLM provider rate limits | Retry with backoff, fallback to rule-based |
| Webhook delivery duplicates | Idempotency key on payment_id |
| High-volume spikes | Kafka backpressure + Redis queue |
| Screening engine sync blocking | Run via asyncio.to_thread() |
