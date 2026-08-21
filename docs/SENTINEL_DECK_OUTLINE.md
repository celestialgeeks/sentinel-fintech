# SENTINEL — 13-Page Deck Outline
**AI-Powered Financial Crime Intelligence** · Finance theme · Human touch · 16:9
Deliverables: `Sentinel_FinTech_Deck.pptx` (PowerPoint) · `Sentinel_FinTech_Deck.pdf` (preview) · `build_sentinel_ppt.py` (generator)

**Design system** — Deep-navy + gold + money-green finance palette; warm paper (#F7F3EA) on human-story pages; editorial serif (Georgia) display + Calibri body. Every engineered slide carries a "human layer" note so analysts/merchants/customers stay the subject.

---

| # | Eyebrow | Slide title | What it covers | Visual |
|---|---------|-------------|----------------|--------|
| 1 | — | **SENTINEL — AI-Powered Financial Crime Intelligence** | Institution, team, tagline; human mission quote | navy title + signal arcs |
| 2 | 01 The Problem | **The human cost of financial crime** | $0.8–2T/yr laundering (FATF), 94% false positives, $20B AML spend, 15B UPI txns/mo | narrative + stat cards |
| 3 | 02 The Mission | **One platform, three protections, people first** | Screen · Detect · Approve pillars + why it matters | 3 pillar cards |
| 4 | 03 How It Fits Together | **One event-driven spine, three risk engines** | Clients → FastAPI → Kafka → 3 engines → 4 data stores | system diagram |
| 5 | 04 Module 1 | **Transaction Screening — AML & sanctions** | Ingest → 5 rules → watchlist/Milvus → APPROVE/REVIEW/BLOCK | pipeline flow |
| 6 | 05 Module 2 | **Real-time fraud detection that learns the user** | Behavioral + XGBoost + Neo4j rings + ensemble + agentic triage | layered flow + example |
| 7 | 06 Module 3 | **Merchant approval — days down to minutes** | RAG/dual-OCR + KYB + transparent 5-signal score | bars + pipeline |
| 8 | 07 The Intelligence | **Four AI techniques, one explainable brain** | LLM entity resolution, GNN, RAG, agentic triage (the "working") | 4 stat cards |
| 9 | 08 Proof | **Measured results — tested, not promised** | AUC 0.98, 100% recall, ~8% FPR, 96% F1, <5 min, <100ms; 42 tests/52% cov | metric tiles |
| 10 | 09 Impact | **What changes for the people inside the system** | Analyst, merchant, customer relief; 60–80% cost reduction | people cards |
| 11 | 10 Engineering | **A stack built to run, measure, and harden** | Runtime · Data · AI/ML · Ops; reliability, audit, security | stack tiles |
| 12 | 11 The Road Ahead | **From prototype to platform** | Live LLMs, GNN, regulatory, scale, crypto roadmap | roadmap rows |
| 13 | — | **Thank you / Q&A** | Team, repo, closing line "trust is the product" | navy closing |

**Story arc:** Why it matters (2) → what we set out to do (3) → how it's built (4) → the three engines (5–7) → the intelligence (8) → proof (9) → human impact (10) → engineering (11) → the future (12) → thank you (13).

**Regenerate after edits:** `cd docs && ../.venv_pptx/bin/python build_sentinel_ppt.py` then open the PPTX in PowerPoint / LibreOffice.
