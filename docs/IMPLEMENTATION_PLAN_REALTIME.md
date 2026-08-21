# Sentinel — Real-Time Implementation Plan

> Phased roadmap for pivoting from batch file-upload screening to real-time webhook-based payment screening with money trail analysis and AI agent verification.

---

## Phase 1: Foundation (Weeks 1-2)

**Goal:** Gateway layer with webhook ingestion and Kafka backbone.

### Files to Create
- `src/gateway/__init__.py`
- `src/gateway/schemas.py` — PaymentEvent, MoneyTrailNode, TrailAnalysis, TrailFlags
- `src/gateway/crm_connectors.py` — BaseCRMConnector, StripeConnector, PlaidConnector
- `src/gateway/ingestion.py` — PaymentWebhookIngestor
- `src/gateway/router.py` — FastAPI router (partial, trails not yet implemented)

### Acceptance Criteria
- [ ] `POST /api/v1/gateway/payment` accepts Stripe/Plaid webhook payloads
- [ ] Normalized PaymentEvent published to Kafka topic `sentinel.payment`
- [ ] Health check `GET /api/v1/gateway/health` returns 200
- [ ] All schemas pass Pydantic validation
- [ ] CRM connectors are abstract base + 2 concrete implementations

### Existing Code to Extend
- `src/api/main.py` — add `app.include_router(gateway_router, prefix="/api/v1/gateway")`
- `docker-compose.yml` — ensure Kafka, Neo4j, PostgreSQL are running

---

## Phase 2: Money Trail Engine (Weeks 3-4)

**Goal:** Graph-based trail analysis with circular flow and structuring detection.

### Files to Create
- `src/gateway/trail.py` — MoneyTrailEngine class
- Extend `src/gateway/router.py` — add `/trail/{id}` endpoint

### MoneyTrailEngine Methods
- `follow_trail(payment_id, depth=5)` — Neo4j graph traversal
- `detect_circular_flow(payment_id)` — detect money looping back
- `detect_structuring(payment_id)` — detect split transactions below thresholds
- `get_counterparty_risk(entity_id)` — check entity risk from PG + Neo4j
- `build_trail_context(payment_id)` — assemble full context for verification

### Acceptance Criteria
- [ ] Trail follows up to 5 hops in Neo4j graph
- [ ] Circular flow detection works (A→B→C→A pattern)
- [ ] Structuring detection flags transactions < threshold from same sender
- [ ] Trail analysis published to Kafka topic `sentinel.trail`
- [ ] Trail context includes: nodes, flags, aggregated risk score

---

## Phase 3: Agent Verification (Weeks 5-6)

**Goal:** AI agent asks questions, gathers context, verifies, then decides.

### Files to Create
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

### Acceptance Criteria
- [ ] Pipeline runs end-to-end: gather → question → verify → decide
- ] 3 decision strategies: rule-based, agentic, hybrid
- [ ] Questions are generated based on missing context, not random
- [ ] Answers are resolved from CRM/DB/knowledge base
- [ ] Final decision includes: APPROVE/REVIEW/BLOCK + confidence + reasoning

---

## Phase 4: Decision Pipeline (Weeks 7-8)

**Goal:** Aggregate all signals, enforce policy, ship decisions.

### Files to Create
- `src/decision/__init__.py`
- `src/decision/engine.py` — DecisionEngine (policy enforcement)
- `src/decision/router.py` — FastAPI router for decision endpoints
- Extend `src/api/main.py` — wire all routers

### DecisionEngine Logic
- Combine: trail risk + screening risk + verification confidence
- Apply policy rules (block if >0.8, review if >0.5, approve if <0.5)
- Log decision with full evidence trail
- Publish decision to Kafka topic `sentinel.decision`

### Acceptance Criteria
- [ ] Decision aggregates all signal sources
- [ ] Policy enforcement is configurable (thresholds in config)
- [ ] Full evidence trail logged for audit
- [ ] Decision published to Kafka
- [ ] All routes wired into FastAPI main.py

---

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
POST /api/v1/gateway/trail/{id}
  → MoneyTrailEngine.follow_trail()
  → Kafka: sentinel.trail
     ↓
POST /api/v1/verification/run
  → VerificationPipeline.run(payment, trail, screening)
  → Kafka: sentinel.decision
     ↓
Result: APPROVE / REVIEW / BLOCK + confidence + evidence
```

### Backward Compatibility
- Existing screening endpoints remain functional
- New gateway/verification endpoints are additive
- Kafka topics are separate (no interference)
- Batch mode can coexist with real-time mode during transition

---

## Tech Stack (Confirmed)

| Component | Technology | Already Built |
|-----------|-----------|---------------|
| API Framework | FastAPI | ✓ |
| Event Streaming | Apache Kafka | ✓ (producer/consumer) |
| Graph DB | Neo4j | ✓ (client + queries) |
| Vector DB | Milvus | ✓ (client) |
| Cache | Redis | ✓ |
| Primary DB | PostgreSQL | ✓ |
| ORM | SQLAlchemy | ✓ |
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
