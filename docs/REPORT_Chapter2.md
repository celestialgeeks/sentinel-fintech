# CHAPTER 2: LITERATURE REVIEW

## 2.1 Overview of Existing Research

### 2.1.1 Traditional AML and Sanctions Screening
Traditional AML screening has relied on rule-based systems since the passage of the Bank Secrecy Act (1970) and the USA PATRIOT Act (2001). Early systems used exact string matching against sanctions lists, which proved inadequate for handling name variations, transliterations, and aliases. Fingerprint matching (Mimno et al., 2016) improved this by incorporating phonetic algorithms (Soundex, Metaphone) and edit distance. However, these approaches still generated high false positive rates.

The introduction of machine learning to sanctions screening marked a significant advance. Sanctions.io's platform (2024) uses NLP-based name matching that achieves 40% fewer false positives than exact matching by handling transliteration issues and nickname variations. Cleareye.ai (2025) combines AI, ML, and LLM-driven natural language capabilities to detect hidden relationships and complex trade-based money laundering patterns.

### 2.1.2 Machine Learning in Fraud Detection
The application of ML to fraud detection has a long history.早期 work by Hahn et al. (2002) demonstrated the effectiveness of neural networks for credit card fraud detection. More recently, XGBoost and LightGBM have become industry standards due to their interpretability and performance on tabular data.

Recent research has focused on deep learning approaches. Chen et al. (2024) demonstrated that Graph Neural Networks (GNNs) achieve 97.5% accuracy in fraud detection compared to 93.2% for traditional ML, primarily by capturing complex relational patterns. The detectGNN framework (2025) addresses inconsistency in GNN application to fraud detection, while Causal Temporal GNNs (CaT-GNN) integrate causal inference with temporal graph learning for credit card fraud.

Federated learning has emerged as a privacy-preserving approach to cross-institutional fraud detection. Visa's acquisition of Featurespace ($925M, 2024) enabled cross-bank pattern learning without sharing raw transaction data. Mastercard's collaborative fraud detection network operates on similar principles.

### 2.1.3 Graph Neural Networks for Financial Crime
Graph-based approaches have gained prominence for detecting organized fraud. Bucher et al. (2017) demonstrated that network analysis can identify money mule networks with 90%+ precision. Neo4j's fraud detection framework (2024) uses Cypher queries to detect round-trip transactions, shared device clusters, and coordinated account creation.

The ASA-GNN model (Tian et al., 2024) employs adaptive sampling and aggregation for transaction fraud detection, achieving superior performance on imbalanced datasets. Contrastive graph neural networks (Deng et al., 2022) address camouflaged fraud detection by learning representations that distinguish fraudulent from legitimate transaction patterns.

### 2.1.4 Large Language Models in Compliance
The application of LLMs to compliance is a rapidly evolving field. The Federal Reserve's research (2024) "Can LLMs Improve Sanctions Screening?" found that LLMs can reduce false positives by 25-40% while maintaining recall above 95%. However, the study also highlighted the importance of human-in-the-loop for high-risk matches.

AMLAgent (Springer, 2024) presents a novel LLM agent architecture for anti-money laundering that combines retrieval-augmented generation with multi-step reasoning. The system encodes FATF, FinCEN, and OFAC guidance into vector stores for compliance queries, achieving traceable and source-backed explanations.

OpenSanctions Pairs (arXiv, 2026) demonstrates that LLM-based entity matching achieves 98.23% F1 score compared to 95.94% for traditional models, using Llama-3.1-8B as the base model. The study highlights the trade-off between accuracy and inference time (~70s vs ~25s per example).

### 2.1.5 Retrieval-Augmented Generation (RAG) for Compliance
RAG architectures have proven effective for regulatory compliance applications. Unit21's approach (2026) encodes AML guidance documents into vector stores for real-time compliance queries, reducing investigation time by 60%. SEON's AML suite (2025) uses RAG to generate automated SAR narratives, reducing report preparation time from hours to minutes.

The AML-MultiAgent-RAG project (Torres, 2025) demonstrates a multi-agent RAG platform using vector databases and AI models to answer AML/CFT compliance queries with quality validation and consistency checking.

### 2.1.6 Merchant Onboarding and KYB
Merchant onboarding has traditionally been a bottleneck, taking 2-5 business days for manual review. AI-powered solutions have compressed this to minutes for low-risk applicants. Alloy (2025) provides perpetual KYB with ongoing monitoring, while Sardine positions around merchant onboarding and risk monitoring for payment businesses.

Bynn (2025) claims 5× faster onboarding with decisions in under 20 seconds, while Gratify Pay focuses on AI underwriting and dynamic risk scoring for ISOs and PayFacs. The EU AI Act (2024) excludes AI systems used for detecting financial fraud from the creditworthiness high-risk category, providing regulatory clarity for deployment.

## 2.2 Commercial Platform Analysis

### 2.2.1 Screening Platforms
| Platform | Key Features | Tech Stack | Pricing |
|----------|-------------|------------|---------|
| Sanctions.io | Real-time API, 75+ watchlists, 350ms response | NLP + ML name matching | Usage-based ($/screen) |
| Checkmarble | Fraud + AML, case management | LLM + rules | Tiered ($99-$999/mo) |
| SEON | AML suite, SAR auto-filing | AI command center | Tiered SaaS |
| ClearEye.ai | Trade-based AML, document digitization | AI + LLM | Enterprise |

### 2.2.2 Fraud Detection Platforms
| Platform | Key Features | Tech Stack | Clients |
|----------|-------------|------------|---------|
| Sardine | Behavioral biometrics, chargeback guarantee | GNN + ML | Brex, FTX, PayPal Crypto |
| Feedzai | Real-time streaming, deep learning | DL + graph | Citi, HSBC, Standard Chartered |
| Featurespace | Adaptive ML, cross-bank learning | AMS | Visa, HSBC, RBS |
| Forter | Identity decisions, retail focus | ML + rules | Nordstrom, ASOS, Sephora |

### 2.2.3 KYB/KYC Platforms
| Platform | Key Features | Coverage | Pricing |
|----------|-------------|----------|---------|
| Alloy | Perpetual KYB, ongoing monitoring | Global | Per-check |
| Persona | Document AI, biometric verification | 190+ countries | Per-verification |
| KYC Hub | ISO 27001, GDPR compliant | Multi-jurisdiction | Per-verification |
| Middesk | US business verification | US-centric | Per-check |

## 2.3 Identification of Research Gaps

### 2.3.1 Lack of Agentic AI in Compliance Workflows
While individual components (screening, fraud detection, KYB) have seen AI adoption, the integration of autonomous agents that can query multiple data sources and synthesize findings remains rare. Most commercial platforms use static rules or basic ML for alert triage, requiring human analysts to investigate each alert manually.

### 2.3.2 Fragmented Tooling
The compliance technology landscape is fragmented, with separate vendors for screening, fraud detection, and KYB. This creates data silos and inconsistent risk assessment across the customer lifecycle. A unified platform that shares context across modules would provide superior risk intelligence.

### 2.3.3 Explainability Deficits
Many AI-powered compliance systems operate as black boxes, making it difficult to provide the deterministic explanations required for regulatory review. The EU AI Act and other regulations demand that AI decisions be traceable to specific evidence and reasoning.

### 2.3.4 Limited Open-Source Solutions
The commercial compliance market is dominated by closed-source platforms with high barriers to entry. There is a lack of production-grade open-source implementations that can serve as reference architectures for academic research and custom deployment.

### 2.3.5 Synthetic Identity Fraud
Synthetic identity fraud surged 311% in North America between Q1 2024 and Q1 2025 (Sumsub, 2025). Current systems are not well-equipped to detect these hybrid identities that combine real and fabricated data to pass KYC checks.

## 2.4 Chapter Summary

This chapter has reviewed the current state of AI-powered compliance technology, identifying key trends in LLM-based entity resolution, graph neural networks for fraud detection, and RAG architectures for regulatory knowledge. The analysis reveals significant gaps in agentic AI integration, platform unification, explainability, and open-source availability — all of which Sentinel addresses.
