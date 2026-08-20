# CHAPTER 5: SYSTEM DESIGN

## 5.1 Architectural Design

### 5.1.1 High-Level Architecture
Sentinel follows an event-driven microservices architecture with four processing layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                        │
│         (Web Dashboard · Mobile API · Third-Party Integrations)│
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS / REST
┌──────────────────────▼──────────────────────────────────────┐
│                   FastAPI API Gateway                         │
│            (Auth · Rate Limiting · Request Routing)           │
└──────┬──────────────────────┬───────────────────────────────┘
       │                      │
┌──────▼──────┐      ┌────────▼────────┐
│  Kafka      │◄────►│  Redis Streams  │
│  (Events)   │      │  (Hot Cache)    │
└──────┬──────┘      └────────┬────────┘
       │                      │
   ┌───▼──────┐          ┌────▼──────────┐
   │ Screening│          │  Fraud Engine │
   │  Engine  │          │   (GNN + ML)  │
   └───┬──────┘          └────┬──────────┘
       │                      │
   ┌───▼──────┐          ┌────▼──────────┐
   │ Milvus   │          │  PostgreSQL   │
   │(Entities)│          │  (Metadata)   │
   └──────────┘          └────┬──────────┘
                              │
                        ┌─────▼──────┐
                        │   Neo4j    │
                        │ (Graph)    │
                        └────────────┘
```

### 5.1.2 Event-Driven Architecture
The Kafka event pipeline decouples ingestion, processing, and alerting:

| Topic | Purpose | Consumers |
|-------|---------|-----------|
| `transactions.raw` | Raw transaction events | Screening Engine, Fraud Engine |
| `transactions.scrubbed` | Post-screening events | Alert Generator, Analytics |
| `fraud.alerts` | Fraud alerts | Triage Agent, Dashboard |
| `merchant.onboarding` | Onboarding events | KYB Pipeline, Risk Scorer |

### 5.1.3 Data Flow Architecture
1. **Ingestion**: Transaction arrives via REST API → validated by Pydantic → published to Kafka
2. **Screening**: Kafka consumer reads event → runs AML rules → checks watchlists → produces result
3. **Fraud Detection**: Transaction features extracted → behavioral profile updated → XGBoost scored → graph analyzed
4. **Merchant Approval**: Document uploaded → OCR parsed → RAG extraction → KYB verification → risk scored
5. **Alert Triage**: High-severity alert → agent queries multiple sources → synthesizes dossier → recommends action

## 5.2 Module Design

### 5.2.1 Transaction Screening Engine
**Purpose**: Screen transactions against AML rules and sanctions watchlists.

**Components**:
1. **Rule Engine** (`src/screening/rules.py`): 5 deterministic rules with weighted scoring
2. **Watchlist Service** (`src/screening/watchlists.py`): OFAC/UN/EU synthetic watchlist data
3. **Entity Resolver** (`src/screening/entity_resolution.py`): LLM + rule-based name matching
4. **Embedding Engine** (`src/screening/embeddings.py`): Vector embeddings for fuzzy matching
5. **Screening Engine** (`src/screening/engine.py`): Orchestrator combining all components

**Input/Output**:
- Input: `TransactionIngest` (transaction_id, amount, currency, sender, receiver, metadata)
- Output: `ScreeningResponse` (risk_score, flags, matched_entities, recommendation, explanation)

### 5.2.2 Real-Time Fraud Detection Engine
**Purpose**: Detect anomalous behavior indicative of account takeover, card fraud, or synthetic identities.

**Components**:
1. **Behavioral Profiler** (`src/fraud/behavioral.py`): Tracks user patterns, computes z-scores
2. **ML Model** (`src/fraud/model.py`): XGBoost classifier trained on synthetic data
3. **Fraud Scorer** (`src/fraud/scorer.py`): Ensemble combining behavioral + ML scores
4. **Alert Triage Agent** (`src/fraud/alert_triage.py`): Multi-source investigation agent

**Detection Capabilities**:
- Amount anomaly (z-score > 2.0)
- Velocity anomaly (>5 txns/hour)
- Geographic impossibility (>5000km in <2 hours)
- Time-of-day anomaly (unusual hour for user)
- Graph-based fraud ring detection (Neo4j)

### 5.2.3 Automated Merchant Approval Engine
**Purpose**: Streamline merchant onboarding with KYB/KYC verification and risk scoring.

**Components**:
1. **Document Extractor** (`src/merchant/kyb.py`): OCR + RAG for document parsing
2. **KYB Verifier** (`src/merchant/kyb.py`): Rule-based verification of extracted data
3. **Risk Scorer** (`src/merchant/risk_scoring.py`): Composite 5-component risk score
4. **Risk Components**: KYB completeness (30%), geographic risk (20%), industry risk (15%), web reputation (15%), sanctions screening (20%)

## 5.3 Database Design

### 5.3.1 Entity-Relationship Diagram
```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Transactions │────▶│ ScreeningResults │     │  FraudAlerts    │
│              │     │                  │     │                 │
│ - id         │     │ - id             │     │ - id            │
│ - txn_id     │     │ - txn_id (FK)    │     │ - txn_id (FK)   │
│ - amount     │     │ - risk_score     │     │ - alert_type    │
│ - currency   │     │ - flags          │     │ - severity      │
│ - sender_id  │     │ - recommendation │     │ - status        │
│ - receiver_id│     │ - explanation    │     │ - risk_score    │
└──────────────┘     └──────────────────┘     └─────────────────┘
       │                                      │
       │                                      │
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ UserProfiles │     │   Merchants      │     │  EntityGraph    │
│              │     │                  │     │                 │
│ - id         │     │ - id             │     │ - id            │
│ - user_id    │     │ - business_name  │     │ - source_id     │
│ - country    │     │ - reg_number     │     │ - target_id     │
│ - device_fp  │     │ - industry       │     │ - rel_type      │
│ - typ_amount │     │ - risk_score     │     │ - weight        │
└──────────────┘     └──────────────────┘     └─────────────────┘
```

### 5.3.2 PostgreSQL Schema
6 tables with proper foreign keys, indexes, and constraints:
- `transactions`: Primary transaction records
- `screening_results`: AML screening outcomes
- `fraud_alerts`: Generated fraud alerts
- `merchants`: Onboarded merchant profiles
- `user_profiles`: Behavioral baselines
- `entity_graph`: Relationship edges

### 5.3.3 Milvus Collection Schema
Collection: `entities`
- Fields: id (VARCHAR), entity_type (VARCHAR), name (VARCHAR), embedding (FLOAT_VECTOR, dim=384), metadata (JSON), score (FLOAT)
- Index: IVF_FLAT with IP metric
- Capacity: 100K+ entity embeddings

### 5.3.4 Neo4j Graph Schema
Nodes: `Transaction`, `User`, `Merchant`, `Device`, `IPAddress`
Relationships: `SENT_FROM`, `RECEIVED_BY`, `USED_DEVICE`, `CONNECTED_TO`, `SAME_IP`
Indexes: On `entity_id`, `user_id`, `device_fingerprint`

## 5.4 API Design

### 5.4.1 Transaction Screening API
```http
POST /api/v1/screening/transactions
Content-Type: application/json

{
  "transaction_id": "tx_987654321",
  "amount": 15000.00,
  "currency": "USD",
  "sender": {"entity_id": "usr_123", "name": "Global Trade Corp", "country": "AE"},
  "receiver": {"entity_id": "merch_456", "name": "Tech Imports LLC", "country": "US"},
  "metadata": {"ip_address": "192.168.1.50", "device_fingerprint": "dev_abc123"}
}

Response:
{
  "transaction_id": "tx_987654321",
  "risk_score": 0.75,
  "flags": ["amount_threshold", "high_risk_jurisdiction"],
  "matched_entities": [...],
  "recommendation": "BLOCK",
  "explanation": "Amount exceeds $10,000 threshold; sender in high-risk jurisdiction (AE)"
}
```

### 5.4.2 Fraud Detection API
```http
POST /api/v1/fraud/check?transaction_id=tx_001&user_id=usr_1&amount=50000&country=US

Response:
{
  "transaction_id": "tx_001",
  "fraud_probability": 0.85,
  "behavioral_z_score": 3.2,
  "velocity_score": 0.6,
  "geo_anomaly": false,
  "time_anomaly": false,
  "ml_score": 0.82,
  "combined_score": 0.78,
  "recommendation": "BLOCK",
  "reason": "Amount anomaly (z=3.2); ML fraud probability=0.82"
}
```

### 5.4.3 Merchant Approval API
```http
POST /api/v1/merchant/onboard
Content-Type: application/json

{
  "business_name": "Acme Corporation",
  "registration_number": "U12345MH2020PTC123456",
  "country": "IN",
  "industry": "E-commerce",
  "website": "https://acme.example.com"
}

Response:
{
  "merchant_id": "merch_001",
  "status": "APPROVED",
  "risk_score": 0.25,
  "kyb_status": "VERIFIED",
  "kyc_status": "NOT_STARTED",
  "ai_summary": "Business registered in India, low-risk industry, clean sanctions check"
}
```

## 5.5 Security Design

### 5.5.1 Authentication
- JWT-based authentication with HS256 algorithm
- Token validation middleware (pass-through for development)
- Rate limiting: 100 requests/minute per client (Redis sliding window)

### 5.5.2 Data Protection
- All credentials via environment variables (no hardcoded secrets)
- PostgreSQL: TLS encrypted connections
- Redis: Password-protected with requirepass
- Neo4j: Auth-enabled with password
- MinIO: Credential-based access

### 5.5.3 Audit Trail
- Structured audit logger writes to JSON log file
- All screening decisions logged with model version, features, confidence
- Immutable event log in Kafka for regulatory review

## 5.6 Deployment Architecture

### 5.6.1 Development Environment
Docker Compose with 10 services:
- `api`: FastAPI application (port 8000)
- `postgres`: PostgreSQL 16 (port 5432)
- `redis`: Redis 7 (port 6379)
- `milvus`: Milvus 2.4 (port 19530)
- `neo4j`: Neo4j 5.22 (ports 7474, 7687)
- `kafka`: Apache Kafka + Zookeeper
- `prometheus`: Metrics collection (port 9090)
- `grafana`: Dashboards (port 3000)
- `etcd` + `minio`: Milvus dependencies

### 5.6.2 Production Environment
Kubernetes deployment with:
- Horizontal Pod Autoscaler (HPA) for API service
- Persistent Volumes for PostgreSQL, Milvus, Neo4j
- Ingress controller for external access
- Pod Disruption Budgets for high availability
- Horizontal Pod Autoscaler based on Kafka lag and CPU
