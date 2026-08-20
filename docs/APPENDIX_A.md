# APPENDIX A: PROJECT SOURCE CODE REPOSITORY STRUCTURE

```
sentinel-fintech/
├── .git/                          # Git version control
├── .github/                       # GitHub Actions workflows
├── .pytest_cache/                 # Pytest cache
├── .coverage                      # Coverage data
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── Dockerfile                     # Production Docker image
├── README.md                      # Project documentation
├── alembic.ini                    # Alembic migration config
├── pyproject.toml                 # Python project config
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # 10-service development stack
├── config/
│   ├── database.yml               # PostgreSQL config
│   ├── kafka.yml                  # Kafka config
│   ├── milvus.yml                 # Milvus config
│   ├── neo4j.yml                  # Neo4j config
│   ├── neo4j.conf                 # Neo4j server config
│   └── init.sql                   # Database initialization
├── docs/
│   ├── IMPLEMENTATION_PLAN.md     # 5-phase roadmap
│   ├── RESEARCH_REPORT.md         # Market/tech/monetization research
│   ├── RESEARCH_SUMMARY.md        # Quick reference
│   ├── TABLE_OF_CONTENTS.md       # Report TOC
│   ├── CODE_REVIEW_PHASE1.md      # Security review
│   ├── CODE_REVIEW_SUMMARY.md     # Review summary
│   ├── REPORT_Certificate.md      # Project certificate
│   ├── REPORT_Acknowledgement.md  # Acknowledgements
│   ├── REPORT_Abstract.md         # Abstract
│   ├── REPORT_Chapter1.md         # Introduction
│   ├── REPORT_Chapter2.md         # Literature Review
│   ├── REPORT_Chapter3.md         # Problem Statement
│   ├── REPORT_Chapter4.md         # Methodology
│   ├── REPORT_Chapter5.md         # System Design
│   ├── REPORT_Chapter6.md         # Implementation
│   ├── REPORT_Chapter7.md         # Testing
│   ├── REPORT_Chapter8.md         # Results
│   ├── REPORT_Chapter9.md         # Conclusion
│   └── REPORT_Chapter10.md        # References
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app factory
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── screening.py       # Screening endpoints
│   │   │   ├── fraud.py           # Fraud endpoints
│   │   │   └── merchant.py        # Merchant endpoints
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py            # JWT auth
│   │       └── rate_limit.py      # Rate limiter
│   ├── screening/
│   │   ├── __init__.py
│   │   ├── engine.py              # ScreeningEngine
│   │   ├── rules.py               # 5 AML rules
│   │   ├── watchlists.py          # OFAC/UN/EU data
│   │   ├── embeddings.py          # Vector embeddings
│   │   ├── entity_resolution.py   # LLM resolver
│   │   └── schemas.py             # Pydantic models
│   ├── fraud/
│   │   ├── __init__.py
│   │   ├── behavioral.py          # Behavioral profiling
│   │   ├── model.py               # XGBoost scorer
│   │   ├── scorer.py              # Ensemble scorer
│   │   ├── alert_triage.py        # Triage agent
│   │   ├── routers.py             # Fraud API router
│   │   └── schemas.py             # Pydantic models
│   ├── merchant/
│   │   ├── __init__.py
│   │   ├── kyb.py                 # KYB verification
│   │   ├── risk_scoring.py        # Composite scoring
│   │   └── schemas.py             # Pydantic models
│   ├── ml/
│   │   └── __init__.py
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── migrate.py             # Alembic runner
│   └── shared/
│       ├── __init__.py
│       ├── db.py                  # PostgreSQL client
│       ├── cache.py               # Redis client
│       ├── kafka.py               # Kafka client
│       ├── vector_db.py           # Milvus client
│       ├── graph_db.py            # Neo4j client
│       ├── models.py              # SQLAlchemy ORM
│       └── audit.py               # Audit logger
├── tests/
│   ├── conftest.py                # Test fixtures
│   ├── test_health.py             # Health endpoint tests
│   ├── test_screening_rules.py    # AML rule tests
│   ├── test_screening_integration.py # Screening integration
│   ├── test_fraud_behavioral.py   # Behavioral tests
│   ├── test_fraud_scorer.py       # Fraud scoring tests
│   ├── test_alert_triage.py       # Triage agent tests
│   ├── test_fraud_router.py       # Fraud API tests
│   └── test_merchant_kyb.py       # Merchant tests
└── scripts/                       # Utility scripts
```
