# Sentinel — End-to-End Implementation Plan

> Comprehensive phased roadmap for building the Sentinel AI-Powered Transaction Screening, Fraud Detection, and Merchant Approval Platform.

---

## Phase 1: Foundation & Architecture (Weeks 1–4)

**Goal:** Establish the project scaffolding, data layer, and core infrastructure.

### Milestone 1.1 — Project Setup (Week 1)
- [ ] Initialise Git repository and remote on GitHub
- [ ] Set up Python 3.11 virtual environment and dependency management (Poetry/pip)
- [ ] Create project directory structure (`src/`, `config/`, `tests/`, `docs/`, `scripts/`)
- [ ] Write `requirements.txt` / `pyproject.toml` with base dependencies
- [ ] Create `.env.example` with all configuration variables
- [ ] Write initial `README.md` with project overview

### Milestone 1.2 — Containerised Infrastructure (Week 2)
- [ ] Write `Dockerfile` for FastAPI application
- [ ] Write `docker-compose.yml` with services:
  - `api` — FastAPI backend
  - `postgres` — PostgreSQL 16
  - `redis` — Redis 7 (caching + message broker)
  - `milvus` — Milvus embedded (vector database)
  - `kafka` — Apache Kafka + Zookeeper
  - `prometheus` + `grafana` — monitoring
- [ ] Create `config/database.yml`, `config/kafka.yml`, `config/milvus.yml`
- [ ] Write database migration scripts (Alembic)
- [ ] Validate all services start and communicate via `docker compose up`

### Milestone 1.3 — Database Schema (Week 3)
- [ ] Design ER diagram for core entities:
  - `transactions` — payment records
  - `screening_results` — AML check outcomes
  - `fraud_alerts` — flagged suspicious activity
  - `merchants` — onboarded merchant profiles
  - `user_profiles` — behavioral profiles
  - `entity_graph` — relationship graph nodes/edges
- [ ] Implement PostgreSQL schema with migrations
- [ ] Create Milvus collection schemas for vector storage:
  - `entities` — sanctioned entity embeddings
  - `transactions` — transaction embeddings for anomaly detection
- [ ] Write PostgreSQL extension setup (pgvector for in-database vectors if needed)

### Milestone 1.4 — Core FastAPI Skeleton (Week 4)
- [ ] Create FastAPI application entry point (`src/api/main.py`)
- [ ] Implement middleware:
  - CORS configuration
  - Authentication (JWT-based)
  - Rate limiting (Redis-backed)
- [ ] Create shared database client (`src/shared/db.py`)
- [ ] Create Redis client (`src/shared/cache.py`)
- [ ] Implement health check endpoint (`GET /health`)
- [ ] Set up structured logging (Python `logging` with JSON output)
- [ ] Write smoke tests for health endpoint

### Phase 1 Deliverables
- [ ] Working `docker compose up` with all services
- [ ] PostgreSQL schema applied and verified
- [ ] Milvus collections created
- [ ] FastAPI health endpoint responding
- [ ] CI pipeline skeleton (GitHub Actions)
- [ ] Phase 1 documentation in `docs/PHASE1_REPORT.md`

---

## Phase 2: Transaction Screening Engine (Weeks 5–8)

**Goal:** Build the AML/sanctions screening engine with LLM-powered entity resolution and vector fuzzy matching.

### Milestone 2.1 — AML Rule Engine (Week 5)
- [ ] Define AML rule categories:
  - Structuring (smurfing) detection
  - High-risk jurisdiction screening
  - Sanctions list matching (OFAC, EU, UN)
  - Volume/frequency anomaly rules
- [ ] Implement rule engine as stateless scoring service
- [ ] Create rule configuration schema in PostgreSQL
- [ ] Write unit tests for each rule category

### Milestone 2.2 — Vector Database Integration (Week 6)
- [ ] Set up Milvus client in `src/shared/vector_db.py`
- [ ] Implement entity embedding generation pipeline:
  - Load sanctioned entity lists (OFAC, EU sanctions)
  - Generate embeddings using sentence-transformers model
  - Store embeddings in Milvus with metadata
- [ ] Create fuzzy matching endpoint:
  - Input: transaction counterparty name
  - Output: similarity scores against sanctions lists
  - Threshold-based alerting
- [ ] Benchmark fuzzy matching accuracy against exact match

### Milestone 2.3 — LLM Entity Resolution (Week 7)
- [ ] Integrate LangChain for LLM-based entity resolution
- [ ] Implement named entity recognition (NER) on transaction data
- [ ] Build entity disambiguation pipeline:
  - "Mohammed Ahmed" vs "M. Ahmed" → same entity?
  - Corporate alias resolution
  - Name transliteration handling
- [ ] Create screening endpoint:
  ```
  POST /api/v1/screening/transactions
  Body: { transaction_id, sender, receiver, amount, currency, metadata }
  Response: { risk_score, flags, matched_entities, recommendation }
  ```
- [ ] Implement Kafka consumer to process screening results

### Milestone 2.4 — Screening API & Integration (Week 8)
- [ ] Finalise `/api/v1/screening/transactions` endpoint
- [ ] Add streaming results via Kafka topic
- [ ] Create screening result storage in PostgreSQL
- [ ] Implement pagination and filtering for screening history
- [ ] Write integration tests for end-to-end screening flow
- [ ] Create sample screening dashboard (basic HTML/JS)

### Phase 2 Deliverables
- [ ] AML rule engine with 4+ rule categories
- [ ] Milvus vector store with 100K+ entity embeddings
- [ ] LLM entity resolution pipeline
- [ ] Functional screening API
- [ ] Phase 2 demo: screen a transaction and receive risk assessment
- [ ] Phase 2 documentation in `docs/PHASE2_REPORT.md`

---

## Phase 3: Real-Time Fraud Detection (Weeks 9–12)

**Goal:** Build behavioral profiling, graph-based anomaly detection, and agentic alert triage.

### Milestone 3.1 — Behavioral Profiling (Week 9)
- [ ] Design user behavioral profile schema:
  - Typical transaction amounts, frequency, timing
  - Geographic patterns
  - Counterparty networks
  - Device fingerprinting
- [ ] Implement feature extraction pipeline (Kafka → Spark/Flink or Python batch)
- [ ] Build baseline profiling model:
  - Statistical baselines (mean, std, percentiles)
  - Time-series feature engineering
- [ ] Store profiles in PostgreSQL + Redis cache

### Milestone 3.2 — ML Fraud Models (Week 10)
- [ ] Prepare fraud detection training data (synthetic + any available data)
- [ ] Implement XGBoost classifier for fraud scoring:
  - Features: behavioral + transactional + graph features
  - Output: fraud probability score
- [ ] Implement isolation forest for novel anomaly detection
- [ ] Create model serving pipeline (ONNX export + FastAPI endpoint)
- [ ] Set up model retraining pipeline with MLflow or similar

### Milestone 3.3 — Graph-Based Analysis (Week 11)
- [ ] Design entity graph schema (nodes: accounts, merchants, devices; edges: transactions)
- [ ] Implement graph storage in PostgreSQL (pg_graphql) or Neo4j
- [ ] Build graph features:
  - Centrality measures
  - Community detection (Louvain)
  - Suspicious pattern detection (round-trip transactions)
- [ ] Create subgraph extraction for alert investigation
- [ ] Integrate graph features into fraud scoring model

### Milestone 3.4 — Agentic Alert Triage (Week 12)
- [ ] Design alert triage agent architecture:
  - Agent receives fraud alert
  - Agent queries relevant context (profile, graph, history)
  - Agent generates triage recommendation (escalate / dismiss / investigate)
- [ ] Implement agent using LangChain agents + tool calling
- [ ] Create alert management API:
  ```
  POST /api/v1/fraud/check
  GET  /api/v1/fraud/alerts
  POST /api/v1/fraud/alerts/{id}/triage
  ```
- [ ] Implement alert escalation workflow
- [ ] Build alert dashboard with prioritisation

### Phase 3 Deliverables
- [ ] Behavioral profiling system with feature pipeline
- [ ] XGBoost fraud model with >85% AUC (target)
- [ ] Graph-based anomaly detection
- [ ] Agentic alert triage system
- [ ] Phase 3 demo: end-to-end fraud detection flow
- [ ] Phase 3 documentation in `docs/PHASE3_REPORT.md`

---

## Phase 4: Automated Merchant Approval (Weeks 13–16)

**Goal:** Build KYB/KYC pipeline with RAG document extraction, web scraping, and risk scoring.

### Milestone 4.1 — KYB/KYC Data Pipeline (Week 13)
- [ ] Design merchant onboarding form/schema
- [ ] Implement document upload endpoint (business registration, ID proofs, bank statements)
- [ ] Create document storage pipeline (local/S3 + metadata in PostgreSQL)
- [ ] Implement document type classification (CNN-based or rule-based)
- [ ] Build data validation pipeline for required fields

### Milestone 4.2 — RAG Document Extraction (Week 14)
- [ ] Set up document processing pipeline:
  - PDF/image parsing (PyMuPDF, Tesseract OCR)
  - Text extraction and chunking
- [ ] Build RAG pipeline with LlamaIndex:
  - Embed extracted text chunks
  - Store in Milvus vector store
  - Query for information extraction (business name, registration number, address)
- [ ] Implement structured extraction using LLM function calling:
  - Extract: business name, registration date, address, director details
  - Validate against known formats
- [ ] Create confidence scoring for extractions

### Milestone 4.3 — Web Scraping & Verification (Week 15)
- [ ] Implement web scraping module:
  - Business registry lookups
  - Website validation (domain age, SSL, content analysis)
  - Social media/profile verification
  - News/sentiment analysis for risk indicators
- [ ] Build verification score from multiple sources
- [ ] Implement competitor/risk check against news databases
- [ ] Create scrape rate limiting and proxy rotation

### Milestone 4.4 — Risk Scoring & Approval (Week 16)
- [ ] Design composite risk scoring model:
  - KYC completeness score
  - RAG extraction confidence
  - Web verification score
  - Sanctions/screening score (reuse Phase 2 engine)
  - Geographic risk score
- [ ] Implement scoring formula with configurable weights
- [ ] Create approval workflow:
  - Auto-approve (low risk)
  - Manual review (medium risk)
  - Reject (high risk)
- [ ] Build merchant API:
  ```
  POST /api/v1/merchant/onboard
  GET  /api/v1/merchant/status/{id}
  GET  /api/v1/merchant/{id}/score
  ```
- [ ] Create merchant dashboard for onboarding status tracking

### Phase 4 Deliverables
- [ ] KYB/KYC document upload and classification
- [ ] RAG-based information extraction pipeline
- [ ] Web scraping and verification module
- [ ] Composite risk scoring engine
- [ ] Automated merchant approval workflow
- [ ] Phase 4 demo: end-to-end merchant onboarding
- [ ] Phase 4 documentation in `docs/PHASE4_REPORT.md`

---

## Phase 5: Integration & Production Hardening (Weeks 17–20)

**Goal:** Unify all modules into a cohesive platform with production-grade infrastructure.

### Milestone 5.1 — Unified Event Pipeline (Week 17)
- [ ] Design Kafka topic architecture:
  - `transactions.raw` — raw transaction events
  - `transactions.scrubbed` — screening results
  - `fraud.alerts` — fraud alerts
  - `merchant.onboarding` — onboarding events
- [ ] Implement event producers in each module
- [ ] Create event consumers for cross-module correlation
- [ ] Build event schema registry (Avro or JSON Schema)
- [ ] Implement event replay capability for debugging

### Milestone 5.2 — Cross-Module Integration (Week 18)
- [ ] Integrate screening results into fraud detection (shared context)
- [ ] Integrate fraud alerts into merchant onboarding (enhanced risk)
- [ ] Build unified risk dashboard:
  - Transaction risk overview
  - Fraud alert summary
  - Merchant approval pipeline status
- [ ] Implement shared context service (Redis-backed)
- [ ] Create unified audit log across all modules

### Milestone 5.3 — Kubernetes Deployment (Week 19)
- [ ] Write Kubernetes manifests:
  - Deployments for each service
  - Services (ClusterIP, LoadBalancer)
  - ConfigMaps and Secrets
  - Ingress rules
- [ ] Implement HPA (Horizontal Pod Autoscaler) policies
- [ ] Set up persistent volumes for PostgreSQL, Milvus
- [ ] Create Helm charts for repeatable deployment
- [ ] Write deployment runbook

### Milestone 5.4 — Monitoring, CI/CD & Documentation (Week 20)
- [ ] Configure Prometheus metrics collection:
  - Application metrics (request latency, error rate)
  - Business metrics (screenings/sec, fraud detection rate)
- [ ] Set up Grafana dashboards
- [ ] Implement alerting rules (PagerDuty/email)
- [ ] Finalise GitHub Actions CI/CD pipeline:
  - Build and test on push
  - Docker image build and push
  - Staging deployment
- [ ] Complete project documentation:
  - API reference
  - Architecture diagrams
  - User guide
  - Deployment guide
- [ ] Prepare final presentation and demo

### Phase 5 Deliverables
- [ ] Fully integrated event-driven pipeline
- [ ] Unified risk dashboard
- [ ] Kubernetes deployment manifests
- [ ] Production monitoring (Prometheus + Grafana)
- [ ] CI/CD pipeline (build → test → deploy)
- [ ] Complete project documentation
- [ ] Final demo and presentation
- [ ] Phase 5 documentation in `docs/PHASE5_REPORT.md`

---

## Key Performance Indicators

| Metric | Target |
|--------|--------|
| Transaction screening latency (p99) | < 500ms |
| Fraud detection accuracy (AUC-ROC) | > 0.90 |
| Screening recall (sanctions matches) | > 95% |
| Merchant onboarding time | < 5 minutes (auto-approved) |
| Alert triage accuracy | > 85% |
| System uptime | > 99.5% |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Kafka single point of failure | Use Kafka with replication; fallback to Redis streams |
| Vector DB performance | Benchmark Milvus; consider ChromaDB as alternative |
| LLM API costs | Implement caching; use local models where possible |
| Data privacy | Encrypt PII at rest and in transit; implement data retention policies |
| Model drift | Set up monitoring; schedule periodic retraining |

---

## Milestone Summary

```
Week  1-4:  Foundation & Architecture  ████████████████████
Week  5-8:  Screening Engine           ████████████████████
Week  9-12: Fraud Detection            ████████████████████
Week 13-16: Merchant Approval          ████████████████████
Week 17-20: Integration & Hardening    ████████████████████
```

---

*Last updated: August 2026*
