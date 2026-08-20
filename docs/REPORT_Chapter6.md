# CHAPTER 6: IMPLEMENTATION

## 6.1 Implementation Environment

### 6.1.1 Development Setup
- **OS**: macOS 26.5.2 (Darwin)
- **Python**: 3.13.9 (Anaconda distribution)
- **Package Manager**: pip with requirements.txt
- **IDE**: Hermes Agent with multi-agent orchestration
- **Version Control**: Git with GitHub (celestialgeeks/sentinel-fintech)

### 6.1.2 Dependencies
Core dependencies (821 source lines, 1291 total statements):
- FastAPI 0.115.0, Uvicorn 0.30.6
- SQLAlchemy 2.0.35 (async), asyncpg 0.29.0
- Pydantic 2.8.2, pydantic-settings 2.4.0
- Milvus 2.4.9, Neo4j 5.24.0, Redis 5.0.8
- LangChain 0.3.1, LlamaIndex 0.11.6
- XGBoost 2.1.1, scikit-learn 1.5.2
- pytest 8.3.2, pytest-asyncio 0.24.0

## 6.2 Phase 1: Foundation & Architecture

### 6.2.1 Project Structure
```
sentinel-fintech/
├── src/
│   ├── api/           # FastAPI application
│   │   ├── main.py    # App factory, lifespan, CORS
│   │   ├── routers/   # API route definitions
│   │   │   ├── screening.py
│   │   │   ├── fraud.py
│   │   │   └── merchant.py
│   │   └── middleware/ # Auth, rate limiting
│   ├── screening/     # AML screening engine
│   │   ├── engine.py  # ScreeningEngine orchestrator
│   │   ├── rules.py   # 5 AML rules
│   │   ├── watchlists.py # OFAC/UN/EU data
│   │   ├── embeddings.py # Vector embeddings
│   │   ├── entity_resolution.py # LLM resolver
│   │   └── schemas.py # Pydantic models
│   ├── fraud/         # Fraud detection
│   │   ├── behavioral.py # Profiling engine
│   │   ├── model.py     # XGBoost classifier
│   │   ├── scorer.py    # Ensemble scorer
│   │   ├── alert_triage.py # Agentic triage
│   │   ├── routers.py   # API endpoints
│   │   └── schemas.py
│   ├── merchant/      # Merchant approval
│   │   ├── kyb.py       # KYB verification
│   │   ├── risk_scoring.py # Composite scoring
│   │   └── schemas.py
│   ├── shared/        # Common utilities
│   │   ├── db.py        # PostgreSQL async client
│   │   ├── cache.py     # Redis client
│   │   ├── kafka.py     # Kafka producer/consumer
│   │   ├── vector_db.py # Milvus client
│   │   ├── graph_db.py  # Neo4j client
│   │   ├── models.py    # SQLAlchemy ORM models
│   │   └── audit.py     # Audit logger
│   └── scripts/       # CLI utilities
│       └── migrate.py   # Alembic runner
├── tests/             # Test suite (42 tests)
├── config/            # Service configurations
├── alembic/           # Database migrations
├── docker-compose.yml # 10-service stack
└── docs/              # Documentation
```

### 6.2.2 Docker Compose Infrastructure
The `docker-compose.yml` defines 10 services with health checks, persistent volumes, and environment-variable-based secrets:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| api | Custom (python:3.11-slim) | 8000 | FastAPI application |
| postgres | postgres:16-alpine | 5432 | Primary database |
| redis | redis:7-alpine | 6379 | Cache + message broker |
| milvus | milvusdb/milvus:v2.4.9 | 19530 | Vector database |
| neo4j | neo4j:5.22 | 7474, 7687 | Graph database |
| kafka | confluentinc/cp-kafka:7.6.1 | 9092 | Event streaming |
| zookeeper | confluentinc/cp-zookeeper:7.6.1 | 2181 | Kafka dependency |
| prometheus | prom/prometheus:latest | 9090 | Metrics collection |
| grafana | grafana/grafana-oss:latest | 3000 | Dashboards |
| etcd + minio | CoreOS/MinIO | - | Milvus dependencies |

### 6.2.3 Database Schema Implementation
Six SQLAlchemy 2.0 ORM models with proper relationships, indexes, and constraints:

```python
class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    sender_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    receiver_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(Enum(TransactionStatusEnum))
    risk_score: Mapped[Optional[float]]
    # Indexes: sender_country, receiver_country, status_risk, created_at
```

### 6.2.4 Alembic Migration Setup
- `alembic.ini`: Async engine configuration
- `alembic/env.py`: Custom migration script with async support
- `src/scripts/migrate.py`: CLI runner with upgrade/downgrade/current/check commands

## 6.3 Phase 2: Transaction Screening Engine

### 6.3.1 AML Rule Engine
Five deterministic rules with weighted scoring:

```python
@dataclass
class RuleResult:
    rule_name: str
    triggered: bool
    weight: float  # 0.0-1.0 contribution to risk score
    detail: str
```

| Rule | Condition | Weight | Description |
|------|-----------|--------|-------------|
| amount_threshold | amount >= $10,000 | 0.3-1.0 | Large transaction flag |
| structuring | 3+ txns < $9,000 in 24h | 0.5-1.0 | Smurfing detection |
| high_risk_jurisdiction | country in sanctioned list | 0.5-1.0 | OFAC/UN/EU countries |
| velocity | >5 txns/hour | 0.3-1.0 | Rapid transaction pattern |
| round_trip | sender_id == receiver_id | 0.9 | Self-circular transaction |

### 6.3.2 Watchlist Implementation
Synthetic watchlist data with 6 entries across OFAC, UN, and EU lists:
- OFAC SDN: Mohammed Ahmad, Global Trade Corp, Petrochem Exports LLC
- UN List: Al-Rashid Khalid, North Star Trading
- EU List: Dmitry Volkov, Tech Imports LLC

### 6.3.3 Vector Embedding Pipeline
- Model: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional)
- Fallback: SHA-256 hash-based placeholder embeddings
- Storage: Milvus collection with IVF_FLAT index
- Search: Hybrid (vector similarity + metadata filter + full-text)

### 6.3.4 LLM Entity Resolution
- Primary: LangChain + ChatOpenAI (gpt-4o-mini)
- Fallback: Exact match + substring match + case-insensitive comparison
- Output: matched_name, confidence (0-1), reasoning, is_alias

### 6.3.5 Screening Engine Orchestrator
```python
class ScreeningEngine:
    def screen(self, txn: TransactionIngest) -> ScreeningResponse:
        # 1. Run AML rules
        rule_results, risk_score = self._rules.evaluate(...)
        # 2. Record for stateful rules
        self._rules.add_transaction(...)
        # 3. Check watchlists
        watchlist_matches = self._check_watchlists(txn)
        # 4. Update risk score with matches
        # 5. Collect flags
        # 6. Build explanation
        # 7. Determine recommendation (APPROVE/BLOCK/REVIEW)
```

## 6.4 Phase 3: Fraud Detection

### 6.4.1 Behavioral Profiling
```python
class BehavioralProfiling:
    def amount_z_score(self, user_id, amount) -> float
    def velocity_check(self, user_id) -> tuple[bool, float]
    def geo_impossibility_check(self, user_id, country) -> tuple[bool, float]
    def time_of_day_anomaly(self, user_id) -> tuple[bool, float]
```

### 6.4.2 XGBoost Fraud Model
- Training: 1000 synthetic samples (900 legitimate, 100 fraud)
- Features: amount, z_score, velocity, geo_anomaly, time_anomaly
- Hyperparameters: n_estimators=50, max_depth=4, scale_pos_weight=9
- Fallback: Rule-based scorer when XGBoost unavailable

### 6.4.3 Ensemble Scoring
```python
combined = min(
    0.35 * ml_score +
    0.25 * min(z_score / 3.0, 1.0) +
    0.20 * velocity_score +
    0.15 * geo_score +
    0.05 * time_score,
    1.0
)
```

### 6.4.4 Agentic Alert Triage
```python
class TriageAgent:
    def triage(self, alert_id, transaction_id, severity, context) -> TriageReport:
        # 1. Query behavioral profile
        # 2. Check graph for connected entities
        # 3. Check IP reputation
        # 4. Check transaction context
        # 5. Synthesize recommendation
```

## 6.5 Phase 4: Merchant Approval

### 6.5.1 RAG Document Extraction
- OCR: Tesseract (fast, CPU) + EasyOCR (accurate, GPU)
- LLM: LangChain + ChatOpenAI for structured extraction
- Fallback: Regex-based rule extraction

### 6.5.2 KYB Verification
```python
class KYBVerifier:
    def verify(self, extracted, merchant_country) -> dict:
        # Check required fields
        # Check risk indicators
        # Check industry risk
        # Return verification_score, issues, risk_level
```

### 6.5.3 Composite Risk Scoring
Five weighted components:
- KYB completeness: 30%
- Geographic risk: 20% (high-risk countries = 0.8)
- Industry risk: 15% (crypto/gambling = 0.7)
- Web reputation: 15%
- Sanctions screening: 20%

## 6.6 Phase 5: Integration

### 6.6.1 API Router Integration
All routers mounted under `/api/v1`:
- `/api/v1/screening/transactions` — POST
- `/api/v1/fraud/check` — POST
- `/api/v1/fraud/alerts` — GET
- `/api/v1/fraud/alerts/{id}/triage` — POST
- `/api/v1/merchant/onboard` — POST
- `/api/v1/merchant/status/{id}` — GET

### 6.6.2 Middleware Implementation
- **Rate Limiter**: Redis-backed sliding window (100 req/min)
- **Auth**: JWT validation (pass-through for development)
- **CORS**: Configurable origins (development: all)

### 6.6.3 Audit Logging
Structured JSON audit events with:
- Timestamp (ISO 8601)
- Action type
- Entity type and ID
- User context
- Result
- Details

## 6.7 Testing Strategy

### 6.7.1 Test Architecture
- **Unit Tests**: Individual module testing (screening rules, behavioral profiling)
- **Integration Tests**: End-to-end screening flow, fraud scoring
- **API Tests**: HTTP endpoint validation with TestClient
- **Mock Fixtures**: SQLite, FakeRedis, FakeMilvus, FakeNeo4j, MockKafka

### 6.7.2 Test Coverage
| Module | Tests | Coverage |
|--------|-------|----------|
| Screening rules | 10 | 98% |
| Screening integration | 6 | 96% |
| Fraud behavioral | 6 | 88% |
| Fraud scorer | 4 | 90% |
| Fraud triage | 4 | 100% |
| Fraud router | 4 | 51% |
| Merchant KYB | 6 | 87% |
| Health/API | 2 | 51% |
| **Total** | **42** | **52%** |

### 6.7.3 Test Results
```
======================== 42 passed, 6 warnings in 1.89s ========================
Required test coverage of 40% reached. Total coverage: 52.45%
```
