#!/usr/bin/env python3
"""
Task brief for Cline — Sentinel FinTech Comprehensive PDF Documentation

This script generates a prompt for Cline to create a deep-dive PDF
documenting the entire Sentinel FinTech project.
"""

BRIEF = """\
# TASK: Create Comprehensive Sentinel FinTech Documentation PDF

## Context
You are working on the Sentinel FinTech project at:
/Users/shreyashsingh/my info/projects/sentinel-fintech/

This is a B.Tech Major Project for CSE-AIML at IPS Academy, Indore.
The project pivoted from batch file-upload screening to real-time webhook-based
payment screening with money trail analysis and AI agent verification.

## Your Job
Create a single, comprehensive, well-illustrated PDF document that teaches
anyone everything about this project. The goal is: after reading this PDF,
a person should be able to explain the entire project in a viva/presentation.

## Source Material (READ ALL BEFORE WRITING)
Read these files in order:
1. docs/RESEARCH_REPORT.md — market research, competitor analysis
2. docs/IMPLEMENTATION_PLAN.md — original 5-phase plan
3. docs/REALTIME_ARCHITECTURE.md — real-time pivot architecture
4. docs/IMPLEMENTATION_PLAN_REALTIME.md — real-time implementation plan
5. README.md — project overview
6. docs/REPORT_Master.md + docs/REPORT_Chapter1.md through Chapter10.md — full report
7. docs/APPENDIX_A.md through APPENDIX_J.md — appendices
8. src/api/main.py — current app structure
9. src/gateway/*.py — gateway module
10. src/verification/*.py — verification module
11. src/decision/*.py — decision engine
12. src/kafka/consumer.py — kafka pipeline
13. src/cache/trail_cache.py — redis cache
14. docker-compose.yml — infrastructure
15. pyproject.toml — dependencies

## PDF Structure (Create this as src/docs/SENTINEL_COMPLETE_GUIDE.md first, then render to PDF)

### Cover Page
- Project title: "Sentinel: AI-Powered Real-Time Transaction Screening & Fraud Detection"
- Subtitle: "From Batch File-Upload to Real-Time Webhook-Based Money Trail Analysis"
- Institution: IPS Academy, Indore (RGPV University)
- Department: CSE-AIML
- Academic Year: 2026-27

### Table of Contents (Auto-generated)

### Chapter 1: The Problem We Solved
- The old way: CSV file uploads, batch processing, hours of delay
- The new way: real-time webhooks, instant decisions, money trail following
- Why this matters: $12B+ in AML fines annually, 311% surge in synthetic fraud
- The gap in existing solutions: no one combines graph analysis + AI agents + real-time

### Chapter 2: How It Works (The Core Narrative)
- **Step-by-step flow** with ASCII diagrams:
  1. Customer connects Stripe/Plaid → webhooks fire
  2. Payment hits /api/v1/gateway/payment
  3. System follows money trail through Neo4j graph (5 hops)
  4. AML watchlists checked (OFAC/UN/EU)
  5. AI agent asks questions, gathers evidence
  6. Decision: APPROVE / REVIEW / BLOCK with confidence score
- Use simple language: "Think of it like a security guard that traces where money has been..."
- Include the "what happens when something is detected" section with all 3 outcomes

### Chapter 3: Technology Deep-Dive (Why We Chose Each Tool)
For EACH technology, explain:
- What it does in simple terms
- Why we chose it over alternatives
- What would happen if we removed it

**Cover these in detail:**
1. **FastAPI** — Why not Flask/Django? (async, auto-docs, 200k req/s)
2. **Apache Kafka** — Why not REST polling? (event-driven, replayable, decoupled)
   - Explain producer/consumer pattern
   - Explain topics: sentinel.payment, sentinel.trail, sentinel.decision
3. **PostgreSQL** — Why not MongoDB? (ACID, JSONB flexibility, pgvector)
4. **Neo4j** — Why not a relational DB for graphs? (Cypher queries, fraud ring detection)
   - Explain circular flow detection query
   - Explain how money trail = graph traversal
5. **Redis** — Why not just in-memory Python dict? (TTL caching, distributed, persistence)
   - Explain trail result caching (5-min TTL)
6. **Milvus** — Why not ChromaDB? (hybrid search, billion-scale, vector+metadata)
7. **Prometheus + Grafana** — What metrics do we track? (latency, error rate, fraud detection rate)
   - Show what a dashboard would look like
8. **OmniRoute** — Why not direct API calls? (free tier, multi-model fallback)

### Chapter 4: The Confidence Score Algorithm (The Math)
Explain the DecisionEngine._aggregate_risk() method in plain English with examples:

```
Risk Score = (Trail Risk × 0.35) + (Screening Risk × 0.25) + (Verification Risk × 0.15) + Policy Flags

Where:
- Trail Risk comes from Neo4j graph analysis (circular flows, structuring, high-risk counterparties)
- Screening Risk comes from AML watchlist matching (OFAC/UN/EU sanctions)
- Verification Risk = 1 - agent confidence (low confidence = high risk)
- Policy Flags add penalties:
  - Circular flow detected: +0.30
  - Structuring detected: +0.20
  - Sanctions match: +0.40
  - Each high-risk counterparty: +0.15 (max +0.30)

Decision Thresholds:
- Score ≥ 0.80 → BLOCK
- Score ≥ 0.50 → REVIEW  
- Score < 0.50 → APPROVE
- Sanctions match → Automatic BLOCK (hard override)
```

Include a worked example with numbers.

### Chapter 5: The Verification Agent (How It Thinks)
Explain the 4-phase pipeline:
1. **GATHER** — What context does it collect? (trail analysis, screening flags, fraud scores)
2. **QUESTION** — How does it decide what to ask? (gaps in trail → "verify source of funds")
3. **VERIFY** — Where do answers come from? (CRM connectors, knowledge base, entity resolution)
4. **DECIDE** — How does it reach a conclusion? (evidence aggregation, confidence scoring)

Explain the 3 strategies:
- RuleBased: Fast, threshold-driven (good for clear cases)
- Agentic: LLM-enhanced reasoning (good for complex cases)
- Hybrid: Rules first, agent for edge cases (best of both)

### Chapter 6: Money Trail Detection (The Cool Part)
Explain how the system follows money:
- **Circular flow detection**: "If money goes A→B→C→A, it's suspicious"
- **Structuring detection**: "If someone sends $1,200 eight times in 24 hours, they're avoiding the $10K reporting threshold"
- **Layering detection**: "If money passes through 5+ accounts quickly, it's being layered"
- **Counterparty risk**: "If the receiver has been linked to fraud before, flag it"

Include the Neo4j Cypher queries used.

### Chapter 7: Customer Experience (What the User Sees)
Describe the customer journey:
1. Sign up → connect Stripe/Plaid
2. Dashboard shows: payments screened, fraud caught, money trails traced
3. Alert receives real-time notifications for BLOCK/REVIEW decisions
4. Can view full evidence trail for any flagged payment
5. Can adjust risk thresholds (be more/less strict)

Include a mockup description of the dashboard UI.

### Chapter 8: Production Readiness
- Docker Compose for local dev
- Kubernetes manifests for production
- CI/CD pipeline (GitHub Actions)
- Monitoring with Prometheus + Grafana
- Alerting on PagerDuty/email
- Disaster recovery (Kafka replay, Redis persistence)

### Chapter 9: Results & Performance
- 18 API endpoints live
- 25 tests passing
- Processing time: <500ms per payment (target)
- Detection accuracy targets: >90% true positive, <15% false positive
- Scalability: Kafka handles 10K+ events/sec

### Chapter 10: What's Next (Future Work)
- Phase 6: Real Neo4j data population
- Phase 7: Live Stripe/Plaid integration (currently mock connectors)
- Phase 8: ML model training with real fraud data
- Phase 9: Mobile app for compliance officers
- Phase 10: Multi-jurisdiction support (India RBI, EU AMLD)

### Appendices
- A: Complete API Reference (all 18 endpoints with request/response)
- B: Database Schema (PostgreSQL tables)
- C: Kafka Topic Schema (event formats)
- D: Neo4j Cypher Queries (full list)
- E: Configuration Guide (.env.example with all variables)
- F: Deployment Guide (Docker + Kubernetes)

## Output Requirements
1. Write the content to: docs/SENTINEL_COMPLETE_GUIDE.md
2. Render it to PDF using the existing slide/skill pipeline or markdown-to-pdf tool
3. Save PDF to: docs/SENTINEL_COMPLETE_GUIDE.pdf
4. The PDF should be 40-60 pages, well-formatted with:
   - Code blocks for technical details
   - ASCII diagrams for architecture
   - Tables for comparisons
   - Callout boxes for key insights
   - Proper chapter headings and page numbers

## Important Notes
- Write in first-person plural ("We built...", "Our approach...")
- Use clear, simple English — this is for a college project defense
- Every technical term should be explained before use
- Include "Why This Matters" callouts throughout
- The goal is depth: someone should learn everything from this document
"""

print(BRIEF)
