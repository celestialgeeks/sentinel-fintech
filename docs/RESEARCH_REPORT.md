# Sentinel: AI-Powered Transaction Screening, Fraud Detection & Merchant Approval
## Research Report — Market, Technology & Monetization
**Prepared:** August 20, 2026 | **Project:** B.Tech Major Project-I, CSE-AIML, IPS Academy, Indore

---

## 1. Market Landscape & Competitive Analysis

### 1.1 Market Size & Growth
- **Global AI Fraud Detection Market:** ~$5.2B (2025) → projected $18.7B by 2030 (CAGR 29.3%)
- **AML/Compliance Market:** ~$28.5B (2025) → $52B by 2030 (CAGR 12.8%)
- **Regulatory pressure:** Global AML fines exceeded $12B in 2024; 311% surge in synthetic identity fraud (Q1 2024–Q1 2025)
- **India-specific:** RBI mandates real-time transaction monitoring; UPI handles 15B+ monthly transactions requiring robust fraud detection

### 1.2 Key Competitors & Their Positioning

| Company | Focus | Tech Stack | Pricing | Strengths | Weaknesses |
|---|---|---|---|---|---|
| **Sanctions.io** | Real-time screening API | NLP + ML name matching, 75+ watchlists | Usage-based ($/screen) | 350ms API response, 60K news sources | No agent triage, limited to screening |
| **Sardine** | Merchant/fraud detection | Behavioral biometrics, graph neural nets | Enterprise SaaS (custom) | 300+ fintech clients, chargeback guarantee | Not open-source, expensive |
| **Feedzai** | Real-time fraud (Tier 1 banks) | Deep learning, graph analytics, streaming | Enterprise | Citi, HSBC, Standard Chartered | Closed platform, high barrier |
| **Featurespace (Visa)** | Adaptive behavioral analytics | AMS (Adaptive Machine Learning) | Usage + platform fee | Visa acquisition ($925M), zero-day detection | Proprietary, not customizable |
| **Checkmarble** | Fraud + AML for fintechs | LLM + rules, case management | Tiered SaaS ($99–$999/mo) | Developer-friendly API, good docs | Newer, limited brand recognition |
| **KYC Hub** | KYC/KYB/AML suite | Document AI, verification APIs | Per-verification pricing | ISO 27001, GDPR compliant, API-first | Modular (pay per feature) |
| **SEON** | Fraud + AML (mid-market) | AI-powered command center | Tiered SaaS | Real-time monitoring, SAR auto-filing | Less scalable for enterprise |
| **Alloy** | Perpetual KYB | Entity resolution, verification APIs | Per-check pricing | Ongoing monitoring, 200+ data sources | US-centric |
| **Persona** | Identity + KYB | Document AI, biometric verification | Per-verification | Strong global coverage | API-only, no custom ML |

### 1.3 Gap Analysis — What Sentinel Can Do Better
1. **Agentic AI triage** — Competitors use static rules or basic ML; none deploy autonomous investigation agents
2. **Unified platform** — Most players specialize in ONE area (screening OR fraud OR KYB); Sentinel covers all three
3. **Open-source core** — All major competitors are closed SaaS; Sentinel can differentiate via open core
4. **Explainability by design** — LLM-powered decisions with deterministic audit trails (regulatory requirement)
5. **Graph + LLM fusion** — Most use either graph OR ML; Sentinel combines both for ring detection

---

## 2. Current Innovations in AI-Powered Compliance

### 2.1 Transaction Screening Innovations
- **LLM-based Entity Resolution:** OpenSanctions Pairs (2026) achieves 98.23% F1 on entity matching using Llama-3.1-8B vs 95.94% for traditional models
- **Vector Database Fuzzy Matching:** Milvus hybrid search (vector + metadata + full-text) enables tolerance for misspellings, aliases, transliterations
- **Phonetic + Semantic Matching:** sanctions.io combines phonetic (Soundex, Metaphone) with semantic (embeddings) for 40% fewer false positives
- **Real-time Watchlist Updates:** Hourly updates across 75+ sanctions lists (OFAC, UN, EU, HM Treasury)
- **Federal Reserve Research (2024):** "Can LLMs Improve Sanctions Screening?" — confirms LLMs reduce false positives by 25-40% but require human-in-the-loop for high-risk matches

### 2.2 Fraud Detection Innovations
- **Graph Neural Networks (GNNs):** 97.5% accuracy vs 93.2% for traditional ML (arXiv 2024, 217 citations). Detects fraud rings, collusion, synthetic identities
- **Agentic AI for Fraud Investigation:** Multi-agent systems where each agent specializes (transaction monitor, identity checker, graph analyst) and collaborates
- **Causal Temporal GNNs (CaT-GNN):** Integrates causal inference with temporal graph learning for credit card fraud (IEEE 2024)
- **Federated Learning:** Visa Featurespace enables cross-bank pattern learning without sharing raw data (privacy-preserving)
- **Behavioral Biometrics:** Keystroke dynamics + mouse movement + smartphone sensors for account takeover detection
- **Open-source projects:** `moov-io/watchman` (AML/CTF/KYC screening), `AML-MultiAgent-RAG` (vector DB + LLM agents for AML queries), `realtime-fraud-detection` (Kafka + Flink + Redis)

### 2.3 KYB/KYC Innovations
- **RAG for Document Extraction:** LlamaIndex pipelines extract business names, registration numbers, UBO (Ultimate Beneficial Owner) from articles of incorporation
- **Dual-engine OCR:** Tesseract (fast, CPU) for clean docs + EasyOCR (accurate, GPU) for complex/handwritten documents
- **Web Scraping for Reputation:** BBB complaints, consumer reviews, chargeback databases, social media analysis
- **Dynamic Risk Scoring:** Industry risk weights (crypto/gaming = high), business longevity, geographic risk, PEP screening
- **AI-Compressed Onboarding:** From 2-5 days → minutes for low-risk applicants (Alloy, Persona, Bynn)

### 2.4 Regulatory & Compliance Tech
- **RAG for Regulatory Knowledge:** Unit21's approach — encode FATF, FinCEN, OFAC guidance into vector stores for compliance queries
- **Explainable AI (XAI):** SHAP values, LIME for model interpretability (required by EU AI Act Annex III)
- **Audit Trail Generation:** Deterministic explanations for every AI decision (regulatory requirement)
- **SAR Auto-Filing:** SEON's platform auto-fills FinCEN SAR/CTR forms with AI-generated narratives

---

## 3. Recommended Technical Architecture

### 3.1 System Architecture (Recommended)
```
┌─────────────────────────────────────────────────────┐
│                   Client Apps                        │
│         (Dashboard · Mobile API · Webhooks)           │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / REST
┌──────────────────────▼──────────────────────────────┐
│                FastAPI API Gateway                    │
│         (Auth · Rate Limiting · Request Routing)      │
└──────┬──────────────────────┬───────────────────────┘
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

### 3.2 Technology Stack (Detailed)

| Component | Primary Choice | Alternative | Rationale |
|---|---|---|---|
| **API Framework** | FastAPI | — | Async-native, 200k+ req/s, auto OpenAPI |
| **Event Streaming** | Apache Kafka | Redis Streams | Replayable, durable, high-throughput |
| **Relational DB** | PostgreSQL 16 | — | ACID, JSONB, pgvector extension |
| **Vector DB** | Milvus 2.4 | ChromaDB (dev) | Distributed, hybrid search, billion-scale |
| **Graph DB** | Neo4j 5 | — | Cypher queries, fraud ring detection |
| **Cache/Hot Store** | Redis 7 | — | Sliding windows, feature store |
| **LLM Framework** | LangChain + LangGraph | LlamaIndex | Agent orchestration, tool calling |
| **RAG Engine** | LlamaIndex | LangChain RAG | Superior retrieval accuracy |
| **ML Training** | scikit-learn + XGBoost | LightGBM | Industry standard, interpretable |
| **Graph Model** | PyG / DGL | neo4j-ml | GNN for fraud ring detection |
| **OCR** | Tesseract + EasyOCR | — | Dual-engine routing |
| **Experiment Tracking** | MLflow | — | Model registry, A/B testing |
| **Containerization** | Docker + Compose | — | Local dev parity |
| **Orchestration** | Kubernetes | — | Production scaling |
| **Monitoring** | Prometheus + Grafana | — | Metrics, alerts, dashboards |

### 3.3 Key Implementation Patterns
1. **Event-Driven Microservices** — Kafka decouples ingestion, processing, alerting
2. **Dual-Engine OCR Routing** — Tesseract for speed, EasyOCR for accuracy
3. **Feature Store (Feast)** — Unified offline/online features, prevents training-serving skew
4. **RAG-Based Fraud Investigation** — LangChain agents retrieve historical cases from vector DB
5. **Graph-Based Fraud Ring Detection** — Neo4j Cypher for connected-entity analysis
6. **Multi-Layer Fraud Scoring** — Rules + ML + Graph → weighted ensemble
7. **Sliding Window Aggregates** — Redis for real-time velocity/geo checks
8. **Hybrid Vector Search** — Milvus: vector + metadata + full-text
9. **MLflow Model Registry** — Versioned models with automatic rollback
10. **Immutable Audit Trail** — All decisions logged with model version + features + confidence

### 3.4 Open-Source Projects to Leverage
- `moov-io/watchman` — AML/CTF/KYC watchlist screening (Go, but API-accessible)
- `luuisotorres/AML-MultiAgent-RAG` — Multi-agent RAG for AML compliance queries
- `OmAnt87/Name-Screening-Engine` — Fuzzy matching for sanctions screening
- `AjayAlluri/realtime-fraud-detection` — Kafka + Flink + Redis real-time pipeline
- `Buffden/ringnet` — Neo4j-based fraud ring detection
- `gholakioko/fraud-detection-mlops` — FastAPI + Kubernetes MLOps pipeline

---

## 4. Monetization Strategy

### 4.1 Pricing Models

| Model | Description | Best For | Pros | Cons |
|---|---|---|---|---|
| **Usage-Based** | $/transaction screened or $/merchant onboarded | Early-stage fintechs | Aligns cost with value, scales naturally | Revenue unpredictability |
| **Tiered SaaS** | Monthly plans (Starter $299, Pro $999, Enterprise custom) | SMB to mid-market | Predictable MRR, simple to sell | May underserve enterprise |
| **Hybrid** | Platform fee + usage overage | Growth-stage | Balance of predictability + upside | Complex to price |
| **Outcome-Based** | % of fraud loss prevented | Enterprise | Maximum value alignment | Hard to measure/attribution |
| **Credit-Based** | Pre-purchased credits, different operations cost different amounts | Mid-market | Flexibility, predictable vendor revenue | Credit exhaustion friction |

### 4.2 Recommended Model for Sentinel
**Hybrid: Platform Fee + Usage-Based**

- **Platform Fee:** $499/mo (covers API access, basic screening, up to 10K transactions/mo)
- **Usage Overage:** $0.005 per additional transaction screened
- **Enterprise:** Custom pricing ($5K+/mo) with SLA, on-premise deployment, dedicated support
- **Add-ons:** 
  - Advanced fraud analytics: +$499/mo
  - Multi-jurisdiction screening: +$299/mo
  - White-label dashboard: +$999/mo
  - On-premise deployment: $50K+ setup + $2K/mo

### 4.3 Target Customer Segments

| Segment | Priority | Pain Point | Willingness to Pay |
|---|---|---|---|
| **Fintech Payment Processors** | 🔴 High | Manual KYB takes 3-5 days, high false positives | $5K-50K/mo |
| **Neobanks** | 🔴 High | Regulatory compliance pressure, fraud losses | $3K-30K/mo |
| **Crypto Exchanges** | 🟡 Medium | AML regulatory requirements, high-risk jurisdiction exposure | $10K-100K/mo |
| **E-commerce Marketplaces** | 🟡 Medium | Merchant fraud, chargeback management | $1K-10K/mo |
| **Traditional Banks** | 🟢 Long-term | Legacy system modernization, false positive reduction | $100K+/mo |
| **Insurance Companies** | 🟢 Long-term | Claims fraud, identity verification | $5K-50K/mo |

### 4.4 Go-to-Market Strategy
1. **Open-core model:** Release screening engine as open-source (GitHub) to build credibility
2. **Freemium API:** 1,000 free screenings/mo for developers
3. **Academic partnerships:** Leverage university affiliation for credibility in India
4. **Content marketing:** Publish compliance research, fraud detection benchmarks
5. **Conference presence:** RegTech, FinTech, AML conferences
6. **Partner channels:** Integration with payment gateways (Razorpay, Stripe India)

---

## 5. Key Performance Indicators (Target)

| Metric | Target | Measurement |
|---|---|---|
| Transaction screening latency (p99) | < 500ms | Prometheus metrics |
| Fraud detection accuracy (AUC-ROC) | > 0.90 | Model evaluation |
| Screening recall (sanctions matches) | > 95% | Comparison against ground truth |
| Merchant onboarding time | < 5 minutes (auto-approved) | End-to-end pipeline |
| Alert triage accuracy | > 85% | Human analyst agreement |
| False positive rate | < 5% | Alert investigation rate |
| System uptime | > 99.5% | Uptime monitoring |
| LLM API cost per screening | < $0.001 | Cost tracking |

---

## 6. Sources & References

### Academic Papers
1. "Graph Neural Networks for Financial Fraud Detection" — arXiv:2411.05815 (217 citations)
2. "Fraud Detection Using Graph Neural Networks: A Survey" — Springer (2024)
3. "OpenSanctions Pairs: Large-Scale Entity Matching with LLMs" — arXiv:2603.11051 (2026)
4. "AMLAgent: A Novel Large Language Model Agent for Anti-money Laundering" — Springer (2024)
5. "Advanced Real-Time Fraud Detection Using RAG-Based LLMs" — arXiv:2501.15290
6. "Causal Temporal Graph Neural Networks for Credit Card Fraud" — IEEE (2024)
7. Federal Reserve: "Can LLMs Improve Sanctions Screening in the Financial System?" (2024)

### Industry Reports
8. "AI Fraud Detection & FinTech 2026" — AIpedia (Sift, Sardine, Riskified, Forter, Feedzai analysis)
9. "Pricing Strategy for AI Fraud Detection" — Monetizely (2025)
10. "Agentic AI for Fraud Detection: A Comprehensive Survey" — IJPREMS (2025)
11. "Fraud Detection and Prevention Market Growth Report" — Global Growth Insights (2026)
12. "Top 10 AI Fraud Detection Companies in USA (2026)" — Cybersecurity News

### Commercial Platforms
13. sanctions.io — Real-time AML screening API
14. Checkmarble — Fraud & AML platform pricing
15. KYC Hub — AI-powered fraud prevention
16. SEON — AML transaction monitoring
17. Unit21 — RAG for risk teams

### Open-Source Projects
18. `moov-io/watchman` — AML/CTF/KYC screening
19. `luuisotorres/AML-MultiAgent-RAG` — Multi-agent RAG for AML
20. `AjayAlluri/realtime-fraud-detection` — Kafka + Flink pipeline
21. `Buffden/ringnet` — Neo4j fraud ring detection
22. `OmAnt87/Name-Screening-Engine` — Fuzzy matching for sanctions

---

*Research compiled: August 20, 2026*
*For: B.Tech Major Project-I, CSE-AIML, IPS Academy, Indore (RGPV)*
