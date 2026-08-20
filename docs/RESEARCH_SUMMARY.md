# Sentinel — Research Summary (Quick Reference)
## Key Findings for Project Report

---

## Market Overview
- **AI Fraud Detection Market:** $5.2B (2025) → $18.7B (2030), CAGR 29.3%
- **AML/Compliance Market:** $28.5B (2025) → $52B (2030), CAGR 12.8%
- India: UPI handles 15B+ monthly transactions; RBI mandates real-time monitoring
- 311% surge in synthetic identity fraud (Q1 2024–Q1 2025)

## Top Competitors
| Platform | Focus | Key Tech | Pricing |
|---|---|---|---|
| Sanctions.io | Screening API | NLP+ML name matching | Usage-based |
| Sardine | Merchant fraud | GNN + behavioral biometrics | Enterprise |
| Feedzai | Real-time fraud | Deep learning + graph | Enterprise |
| Checkmarble | Fraud+AML | LLM+rules+case mgmt | $99-$999/mo |
| SEON | Fraud+AML | AI command center | Tiered SaaS |
| KYC Hub | KYC/KYB/AML | Document AI | Per-verification |

## Key Innovations (2024-2026)
1. **LLM Entity Resolution** — OpenSanctions Pairs: 98.23% F1 (vs 95.94% traditional)
2. **Graph Neural Networks** — 97.5% fraud detection accuracy (vs 93.2% traditional ML)
3. **Agentic AI Triage** — Multi-agent systems for autonomous fraud investigation
4. **RAG for Compliance** — Vector-stored regulatory knowledge for explainable decisions
5. **Dual-Engine OCR** — Tesseract (speed) + EasyOCR (accuracy) routing

## Recommended Tech Stack
- **Backend:** FastAPI + Python 3.11
- **Streaming:** Apache Kafka + Redis Streams
- **Databases:** PostgreSQL 16 (relational) + Milvus (vectors) + Neo4j (graph)
- **AI/LLM:** LangChain (agents) + LlamaIndex (RAG)
- **ML:** XGBoost + PyTorch Geometric (GNN)
- **OCR:** Tesseract + EasyOCR (dual-engine)
- **DevOps:** Docker + Kubernetes + Prometheus + Grafana

## Monetization
- **Model:** Hybrid — Platform fee + usage-based
- **Starter:** $499/mo (10K transactions/mo included)
- **Overage:** $0.005 per additional transaction
- **Enterprise:** $5K+/mo (SLA, on-premise, dedicated support)
- **Target:** Fintechs, Neobanks, Crypto exchanges, E-commerce marketplaces

## Research Gaps This Project Fills
1. Agentic AI in compliance workflows (most platforms use static rules)
2. Unified screening + fraud + KYB in one platform (market is fragmented)
3. Open-source production-grade solution (all competitors are closed SaaS)
4. Explainability-by-design with deterministic audit trails
5. Graph + LLM fusion for fraud ring detection

## Key References
1. arXiv:2411.05815 — GNN for Financial Fraud Detection (217 citations)
2. arXiv:2603.11051 — OpenSanctions Pairs (LLM entity matching)
3. arXiv:2501.15290 — RAG-Based LLMs for Fraud Detection
4. Federal Reserve (2024) — "Can LLMs Improve Sanctions Screening?"
5. IJPREMS (2025) — "Agentic AI for Fraud Detection: A Comprehensive Survey"
