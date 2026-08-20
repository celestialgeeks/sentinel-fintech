# CHAPTER 3: PROBLEM STATEMENT

## 3.1 Problem Description

### 3.1.1 The Compliance Challenge in Modern FinTech
Financial institutions process billions of transactions daily, each requiring screening against sanctions lists, evaluation for fraud, and compliance with KYC/KYB regulations. The scale and velocity of modern payment systems — UPI's 15 billion monthly transactions in India alone, Visa's 200+ million daily transactions globally — make manual review impossible.

Current systems rely on hardcoded rules that:
- Generate 94% false positives, wasting investigator time
- Miss sophisticated fraud patterns (structuring, round-trips, fraud rings)
- Cannot adapt to new fraud typologies without manual rule updates
- Operate in silos (screening separate from fraud separate from KYB)

### 3.1.2 Limitations of Rule-Based Systems
Rule-based AML systems suffer from several fundamental limitations:

1. **Rigidity**: Rules must be manually authored and updated. New fraud patterns require rule changes, creating lag between emergence and detection.
2. **False Positives**: Broad rules generate excessive alerts. A $10,000 threshold catches legitimate transactions from high-volume businesses.
3. **Context Blindness**: Rules evaluate transactions in isolation, ignoring sender history, recipient relationships, and behavioral patterns.
4. **Name Matching Failures**: Exact string matching fails on transliterations (محمد أحمد vs Mohammed Ahmed), nicknames, and corporate aliases.

### 3.1.3 The Rise of AI-Generated Fraud
Generative AI has lowered the barrier for sophisticated fraud:
- **Synthetic identities**: AI can generate realistic but fabricated identity documents
- **Deepfake impersonation**: Voice and video deepfakes bypass biometric verification
- **Coordinated attacks**: AI can orchestrate multi-account fraud rings with human-like behavior patterns
- **Adversarial examples**: Fraudsters can craft transactions designed to evade rule-based detection

These developments demand AI-powered detection systems that can learn and adapt.

## 3.2 Research Questions

1. **RQ1**: How effective are LLM-based entity resolution and vector embedding matching compared to traditional rule-based screening for AML compliance?
2. **RQ2**: Can a hybrid system combining behavioral profiling, graph analysis, and ML classification outperform rule-based fraud detection?
3. **RQ3**: How effective is agentic AI for pre-investigating fraud alerts and synthesizing risk dossiers?
4. **RQ4**: What architectural patterns enable real-time compliance processing at scale?
5. **RQ5**: How can explainability be embedded in AI-powered compliance systems for regulatory audit?

## 3.3 Objectives

### 3.3.1 Primary Objective
Design and implement Sentinel — an integrated AI-powered platform for transaction screening, fraud detection, and merchant approval that reduces false positives, accelerates workflows, and maintains regulatory compliance.

### 3.3.2 Specific Goals
1. Implement an AML screening engine with 5 deterministic rules and vector-based watchlist matching achieving >95% recall
2. Build a fraud detection system combining behavioral profiling, XGBoost classification, and graph analysis achieving >90% AUC-ROC
3. Develop an agentic triage system that investigates alerts and produces risk dossiers with >85% accuracy
4. Create a KYB pipeline with RAG document extraction reducing onboarding time to <5 minutes
5. Ensure all AI decisions are explainable with deterministic audit trails

### 3.3.3 Measurable Targets
| Target | Value | Measurement |
|--------|-------|-------------|
| Screening recall | >95% | Ground-truth watchlist match rate |
| False positive rate | <10% | Alert investigation rate |
| Fraud AUC-ROC | >0.90 | Model evaluation |
| Onboarding time | <5 min | End-to-end pipeline timing |
| Triage accuracy | >85% | Human analyst agreement |
| System latency p99 | <500ms | Load testing |

## 3.4 System Requirements

### 3.4.1 Functional Requirements
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Screen transactions against OFAC/UN/EU watchlists | Critical |
| FR-2 | Detect structuring (multiple small transactions below threshold) | Critical |
| FR-3 | Flag high-risk jurisdiction transactions | Critical |
| FR-4 | Detect velocity anomalies (>5 txns/hour) | High |
| FR-5 | Detect round-trip transactions | High |
| FR-6 | Compute behavioral z-scores for amount anomalies | High |
| FR-7 | Detect geographic impossibility | Medium |
| FR-8 | Provide APPROVE/BLOCK/REVIEW recommendation | Critical |
| FR-9 | Generate human-readable explanations | Critical |
| FR-10 | Onboard merchants with KYB risk scoring | High |

### 3.4.2 Non-Functional Requirements
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Screening latency (p99) | <500ms |
| NFR-2 | System uptime | >99.5% |
| NFR-3 | Test coverage | >40% |
| NFR-4 | API documentation | OpenAPI/Swagger |
| NFR-5 | Audit trail | Immutable log |
| NFR-6 | Data encryption | AES-256 at rest, TLS 1.3 in transit |
| NFR-7 | Container security | Non-root user, minimal base image |
