# CHAPTER 1: INTRODUCTION

## 1.1 Background

The global financial landscape is undergoing a profound transformation driven by digital payments, real-time banking, and the proliferation of FinTech platforms. According to the Reserve Bank of India, UPI alone processed over 15 billion transactions in a single month in 2025, while global digital payment volumes are projected to exceed $10 trillion annually by 2027. This exponential growth in transaction volume has created unprecedented challenges for financial institutions in detecting and preventing financial crime.

Anti-Money Laundering (AML) and Know Your Customer (KYC) regulations require financial institutions to screen every transaction against global sanctions lists, monitor for suspicious patterns, and verify the identity of business customers. The Financial Action Task Force (FATF) estimates that money laundering accounts for 2-5% of global GDP, approximately $800 billion to $2 trillion annually. In response, financial institutions have traditionally relied on rule-based systems that flag transactions matching predefined criteria such as transaction amount thresholds, geographic restrictions, and velocity checks.

However, these legacy systems suffer from critical limitations. The global average false positive rate for AML screening is approximately 94%, meaning that 94 out of every 100 alerts generated are ultimately determined to be benign. This results in enormous operational costs — banks spend an estimated $20 billion annually on AML compliance, with investigation costs averaging $50-100 per alert. Furthermore, rule-based systems cannot detect sophisticated fraud schemes such as structuring (smurfing), where transactions are deliberately kept below reporting thresholds, or coordinated fraud rings that operate across multiple accounts and jurisdictions.

The emergence of generative AI and large language models (LLMs) has created new opportunities for compliance automation. Recent research by the Federal Reserve (2024) demonstrated that LLMs can reduce false positives in sanctions screening by 25-40% while maintaining recall above 95%. Similarly, Graph Neural Networks (GNNs) have achieved 97.5% accuracy in fraud detection compared to 93.2% for traditional machine learning approaches, primarily by capturing complex relational patterns that rule-based systems miss.

## 1.2 Importance and Relevance

### 1.2.1 Regulatory Pressure
The regulatory landscape for financial compliance has tightened significantly in recent years. In 2024, global AML fines exceeded $12 billion, with enforcement shifting from traditional banks to fintechs, crypto exchanges, and payment service providers. The EU AI Act (2024) classifies AI systems used for fraud detection and AML compliance as high-risk, requiring explainability, auditability, and human oversight. India's Unique Identification Authority (UIDAI) and Reserve Bank of India (RBI) have introduced stringent KYC/KYB requirements for digital payment platforms.

### 1.2.2 Economic Impact
The economic cost of financial crime is staggering. According to Interpol, organized crime syndicates generate approximately $1.6 trillion annually through fraud, money laundering, and terrorist financing. For FinTech companies, the cost of a single compliance failure can be existential — regulatory fines, reputational damage, and loss of banking partnerships. A 2025 study by Deloitte found that companies with AI-powered compliance systems reduced fraud losses by 70% and operational costs by 45% compared to rule-based counterparts.

### 1.2.3 Technical Relevance
From a computer science perspective, Sentinel addresses several challenging problems at the intersection of multiple AI/ML domains:

1. **Semantic Entity Resolution**: Matching transaction entities against watchlists despite misspellings, aliases, and name variations requires NLP and embedding-based similarity search.
2. **Real-Time Anomaly Detection**: Detecting fraudulent patterns in streaming data at scale requires efficient feature engineering and model serving.
3. **Graph-Based Relationship Analysis**: Identifying fraud rings and mule networks requires graph algorithms that can operate on billion-scale entity graphs.
4. **Agentic AI Workflows**: Autonomous investigation agents that query multiple data sources and synthesize findings represent the frontier of applied AI.
5. **Explainable AI**: Regulatory requirements demand that every AI decision be traceable to specific evidence and reasoning.

### 1.2.4 Academic Contribution
This project contributes to the academic literature on AI-driven financial crime prevention by:
- Demonstrating a production-grade implementation of a unified AML/fraud/KYB platform
- Providing open-source reference implementations of entity resolution, behavioral profiling, and agentic triage
- Establishing benchmark evaluation metrics for hybrid rule-based + ML compliance systems
- Documenting the architectural patterns for event-driven microservices in the compliance domain

## 1.3 Scope and Limitations

### 1.3.1 Scope
The Sentinel platform covers three core operational domains:

1. **Transaction Screening Engine**: Real-time AML and sanctions screening of payment transactions against global watchlists (OFAC, UN, EU) using vector-based fuzzy matching and LLM-powered entity resolution. The system evaluates transactions against five deterministic rules (amount threshold, structuring, high-risk jurisdiction, velocity, round-trip) and produces a risk score with an APPROVE/BLOCK/REVIEW recommendation.

2. **Real-Time Fraud Detection**: Behavioral profiling of users based on transaction history, combined with an XGBoost fraud classifier and graph-based relationship analysis. The system detects amount anomalies (z-score > 2.0), velocity anomalies (>5 transactions/hour), geographic impossibility (>5000km in <2 hours), and time-of-day anomalies. An agentic triage system investigates high-severity alerts by querying multiple data sources.

3. **Automated Merchant Approval**: KYB/KYC pipeline for onboarding new merchants, including document extraction (OCR + RAG), web-based reputation analysis, and composite risk scoring across five dimensions (KYB completeness, geographic risk, industry risk, web reputation, sanctions screening).

### 1.3.2 Limitations
Several limitations are acknowledged:

1. **Synthetic Data**: Due to the sensitive nature of financial data and privacy regulations, the system uses synthetic transaction data for development and testing. Production deployment would require real transaction data and formal model validation.
2. **Limited Watchlist Coverage**: The current implementation uses a synthetic watchlist of ~6 entries. Production would integrate live sanctions data feeds (e.g., sanctions.io, Dow Jones, Refinitiv).
3. **No Live LLM Integration**: The LLM-based entity resolution and RAG document extraction are implemented as architectural frameworks with graceful fallbacks to rule-based methods. Live API integration requires API keys and cost management.
4. **Single-Jurisdiction Focus**: While the architecture supports multi-jurisdiction screening, the current rule set is designed for Indian and international compliance requirements. Regional-specific rules would need to be added for deployment in specific markets.
5. **No Blockchain Integration**: Crypto-specific screening (chain analysis, mixer detection) is not implemented but is planned for future work.

## 1.4 Project Objectives

### 1.4.1 Primary Objectives
1. Design and implement a unified AI-powered platform for AML screening, fraud detection, and merchant approval
2. Achieve >95% recall on watchlist matching with <10% false positive rate
3. Reduce merchant onboarding time from days to minutes for low-risk applicants
4. Build an explainable, auditable system suitable for regulatory review
5. Create an open-source reference implementation that can be extended by the community

### 1.4.2 Measurable Targets
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Screening recall | >95% | Comparison against ground-truth watchlist matches |
| False positive rate | <10% | Alert investigation rate in controlled tests |
| Fraud detection AUC-ROC | >0.90 | Model evaluation on synthetic fraud dataset |
| Merchant onboarding time | <5 min (auto-approved) | End-to-end pipeline timing |
| Alert triage accuracy | >85% | Agreement with human analyst decisions |
| System latency (p99) | <500ms | Production load testing |
| Test coverage | >40% | pytest-cov measurement |

## 1.5 Report Organization

This report is organized into ten chapters. Chapter 2 reviews existing literature on AI-powered compliance systems. Chapter 3 defines the problem statement and research questions. Chapter 4 describes the methodology and technical approach. Chapter 5 presents the system architecture and design. Chapter 6 details the implementation. Chapter 7 covers testing and validation. Chapter 8 presents results and discussion. Chapter 9 concludes with findings and future work. Chapter 10 contains references and appendices.
