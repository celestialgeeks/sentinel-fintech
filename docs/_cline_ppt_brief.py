#!/usr/bin/env python3
"""
Task brief for Cline — Sentinel FinTech PPT + Finance Theme Research
"""

BRIEF = """\
# TASK 1: Research Finance-Themed PPT Templates

## Context
You are working on the Sentinel FinTech project at:
/Users/shreyashsingh/my info/projects/sentinel-fintech/

## Your Job — Research Phase (Do this FIRST)
Search the web for finance-themed PowerPoint templates that would work for a college major project presentation about a fintech/fraud detection platform.

Search for:
1. "fintech ppt template dark blue"
2. "financial technology presentation template professional"
3. "banking fraud detection powerpoint template"
4. "fintech startup pitch deck template"

Find 3-5 good options. For each, note:
- Template name
- Where to download (URL)
- Key features (color scheme, slide count, style)
- Why it fits this project

Output your research to: docs/PPT_TEMPLATE_RESEARCH.md

## Your Job — PPT Creation Phase (After research)
Create a 15-slide PowerPoint presentation for the college major project defense.

Read these files first:
1. README.md
2. docs/REALTIME_ARCHITECTURE.md
3. docs/IMPLEMENTATION_PLAN_REALTIME.md
4. docs/RESEARCH_REPORT.md (first 100 lines)
5. src/api/main.py (to see current endpoints)

Then create the PPT using python-pptx at: projects/sentinel-fintech/exports/Sentinel_Major_Project.pptx

## Slide Structure (15 Slides)

1. **Title Slide** — "Sentinel: AI-Powered Real-Time Transaction Screening & Fraud Detection" + team names + institution
2. **Problem Statement** — Why does this project exist? (batch file upload is slow, fraud is rising, $12B fines)
3. **Our Solution** — Real-time webhook-based screening with money trail analysis
4. **System Architecture** — High-level diagram showing all components
5. **Technology Stack** — Table of technologies with why we chose each
6. **How It Works — Step 1: Ingestion** — Webhook → Normalization → Kafka
7. **How It Works — Step 2: Trail Analysis** — Neo4j graph traversal, circular flow detection
8. **How It Works — Step 3: Screening** — AML watchlists, sanctions matching
9. **How It Works — Step 4: Verification** — AI agent asks questions, gathers evidence
10. **How It Works — Step 5: Decision** — APPROVE/REVIEW/BLOCK with confidence score
11. **The Confidence Score Algorithm** — The math behind the decision (weighted scoring)
12. **Customer Dashboard** — What the customer sees (mockup description)
13. **Results & Metrics** — 18 endpoints, 25 tests, <500ms latency target
14. **Future Scope** — What's next (Phase 6-10)
15. **Thank You / Q&A** — Contact info, GitHub repo link

## PPT Design Rules
- Use the finance-themed template you found in research
- Dark blue/navy color scheme (professional, trust)
- Clean layouts, not cluttered
- Use icons where possible (shield, graph, alert)
- Keep text minimal — bullets, not paragraphs
- Each slide should be readable in 30 seconds
- Include the architecture diagram on slide 4 (use ASCII or describe it)
- Add code snippets on slides 11 (algorithm) to show technical depth
- End with a strong closing slide

## Output
- PPT saved to: projects/sentinel-fintech/exports/Sentinel_Major_Project.pptx
- Research saved to: docs/PPT_TEMPLATE_RESEARCH.md
"""

print(BRIEF)
