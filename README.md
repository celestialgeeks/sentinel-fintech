# Sentinel — AI-Powered Transaction Screening, Fraud Detection & Merchant Approval

> An intelligent financial security platform for real-time AML screening, fraud detection, and automated merchant onboarding.

**Academic Project** — B.Tech Major Project-I, 2026-27  
**Institution:** IPS Academy, Indore (RGPV University, CSE-AIML Department)  
**Developed by:** Shreyash Singh ([@celestialgeeks](https://github.com/celestialgeeks))

---

## Overview

Sentinel is a comprehensive fintech security platform that combines:

- **Transaction Screening Engine** — AML/sanctions compliance using LLM-powered entity resolution and vector database fuzzy matching
- **Real-time Fraud Detection** — Behavioral profiling, graph-based anomaly detection, and agentic alert triage
- **Automated Merchant Approval** — KYB/KYC workflows with RAG document extraction, web scraping, and dynamic risk scoring

All three modules operate on a unified event streaming backbone, sharing risk context in real time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Gateway | FastAPI + Uvicorn |
| Data Store | PostgreSQL (primary) + Redis (cache/broker) |
| Vector DB | Milvus (fuzzy matching & entity resolution) |
| ML / LLM | LangChain + LlamaIndex + HuggingFace Transformers |
| Streaming | Apache Kafka (event pipeline) |
| Containerisation | Docker + Docker Compose |
| Orchestration | Kubernetes (production) |
| Monitoring | Prometheus + Grafana |
| CI/CD | GitHub Actions |
| Testing | pytest + Locust |

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                     Client Apps                          │
│  (Web Dashboard · Mobile API · Third-party Integrations) │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / REST
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Gateway                        │
│           (Auth · Rate Limiting · Request Routing)       │
└──────┬──────────────────────┬───────────────────────────┘
       │                      │
┌──────▼──────┐      ┌────────▼────────┐
│ Kafka Topic │◄────►│  Event Bus      │
│  (Redis)    │      │  (Kafka)        │
└──────┬──────┘      └────────┬────────┘
       │                      │
   ┌───▼──────┐          ┌────▼──────────┐
   │ Screening│          │  Fraud Engine │
   │  Engine  │          │   (Graph +    │
   │(AML/LLM) │          │  ML models)   │
   └───┬──────┘          └────┬──────────┘
       │                      │
   ┌───▼──────┐          ┌────▼──────────┐
   │ Milvus   │          │  ML Models    │
   │(Vector)  │          │  (XGBoost /   │
   └──────────┘          │  Neural Nets) │
                         └────┬──────────┘
                               │
                         ┌─────▼──────┐
                         │ PostgreSQL │
                         │  (Primary) │
                         └────────────┘
```

---

## Quick Start

### Prerequisites

- Docker Desktop (v24+) with Compose plugin
- Python 3.11+
- Git

### One-command local setup

```bash
# Clone the repo
git clone https://github.com/celestialgeeks/sentinel-fintech.git
cd sentinel-fintech

# Start all services
docker compose up -d

# Run migrations
docker compose exec api python -m src.scripts.migrate

# Verify health
curl http://localhost:8000/health
```

### Environment configuration

```bash
cp .env.example .env
# Edit .env with your settings (API keys, DB passwords, etc.)
```

### Run tests

```bash
docker compose run --rm api pytest tests/ -v
```

---

## Project Structure

```
sentinel-fintech/
├── src/
│   ├── api/                 # FastAPI application & routes
│   │   ├── routers/         # Endpoint modules
│   │   ├── middleware/      # Auth, CORS, rate limiting
│   │   └── main.py          # Application entry point
│   ├── screening/           # Transaction Screening Engine
│   │   ├── aml.py           # AML rule engine
│   │   ├── entity_resolution.py
│   │   └── vector_matcher.py
│   ├── fraud/               # Fraud Detection Engine
│   │   ├── behavioral.py    # Behavioral profiling
│   │   ├── graph_analysis.py
│   │   └── alert_triage.py  # Agentic alert triage
│   ├── merchant/            # Merchant Approval Engine
│   │   ├── kyb_kyc.py       # KYB/KYC workflows
│   │   ├── rag_extractor.py # RAG document extraction
│   │   └── risk_scoring.py  # Dynamic risk scoring
│   ├── ml/                  # ML models & training
│   │   ├── models/          # Saved model artifacts
│   │   └── training/        # Training pipelines
│   ├── shared/              # Shared utilities
│   │   ├── db.py            # Database connections
│   │   ├── cache.py         # Redis client
│   │   ├── kafka.py         # Kafka producer/consumer
│   │   └── vector_db.py     # Milvus client
│   └── scripts/             # Migration & utility scripts
├── config/
│   ├── database.yml         # Database configuration
│   ├── kafka.yml            # Kafka configuration
│   └── milvus.yml           # Vector DB configuration
├── tests/
│   ├── api/                 # API endpoint tests
│   ├── screening/           # Screening engine tests
│   ├── fraud/               # Fraud engine tests
│   └── merchant/            # Merchant engine tests
├── docs/
│   └── IMPLEMENTATION_PLAN.md
├── scripts/                 # Build, deploy & utility scripts
├── docker-compose.yml       # Development orchestration
├── Dockerfile               # Production image
├── .env.example             # Environment variables template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Development Phases

| Phase | Title | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **Phase 1** | Foundation & Architecture | Weeks 1–4 | Scaffold, DB schema, vector store, core services, basic APIs |
| **Phase 2** | Screening Engine | Weeks 5–8 | AML rule engine, entity resolution, fuzzy matching |
| **Phase 3** | Fraud Detection | Weeks 9–12 | Behavioral profiling, graph analysis, alert triage agents |
| **Phase 4** | Merchant Approval | Weeks 13–16 | KYB/KYC pipeline, RAG extraction, risk scoring |
| **Phase 5** | Integration & Hardening | Weeks 17–20 | End-to-end pipeline, CI/CD, monitoring, documentation |

See **[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** for the full phased plan.

---

## API Endpoints (Planned)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/screening/transactions` | Submit a transaction for AML screening |
| `GET` | `/api/v1/screening/results/{id}` | Get screening result by ID |
| `POST` | `/api/v1/fraud/check` | Submit transaction for fraud analysis |
| `GET` | `/api/v1/fraud/alerts` | List fraud alerts |
| `POST` | `/api/v1/merchant/onboard` | Submit merchant for KYB/KYC approval |
| `GET` | `/api/v1/merchant/status/{id}` | Check onboarding status |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/metrics` | Prometheus metrics |

---

## License

Academic project — IPS Academy, Indore.

---

## Acknowledgements

- IPS Academy, Indore — CSE-AIML Department
- RGPV University — Academic guidance
