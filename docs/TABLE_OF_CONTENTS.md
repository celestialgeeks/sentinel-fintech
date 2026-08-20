# Sentinel — Table of Contents
## B.Tech Major Project-I Report (2026-27)
**CSE-AIML Department, IPS Academy, Indore (RGPV University)**

---

### FRONT MATTER
| Page | Content |
|------|---------|
| i | Title Page |
| ii | Certificate |
| iii | Acknowledgement |
| iv | Abstract |
| v | Table of Contents |
| vi | List of Tables |
| vii | List of Figures |
| viii | List of Abbreviations |

---

### CHAPTER 1: INTRODUCTION
| Section | Page |
|---------|------|
| 1.1 Background | 1 |
| 1.2 Problem Statement | 2 |
| &nbsp;&nbsp;&nbsp;&nbsp;1.2.1 The Compliance Challenge in Modern FinTech | 2 |
| &nbsp;&nbsp;&nbsp;&nbsp;1.2.2 Limitations of Rule-Based Systems | 3 |
| &nbsp;&nbsp;&nbsp;&nbsp;1.2.3 The Rise of AI-Generated Fraud | 3 |
| 1.3 Objectives | 4 |
| &nbsp;&nbsp;&nbsp;&nbsp;1.3.1 Primary Objectives | 4 |
| &nbsp;&nbsp;&nbsp;&nbsp;1.3.2 Measurable Targets | 5 |
| 1.4 Scope and Limitations | 5 |
| 1.5 Project Significance | 6 |
| 1.6 Report Organization | 7 |

---

### CHAPTER 2: LITERATURE REVIEW
| Section | Page |
|---------|------|
| 2.1 Overview of Existing Research | 8 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.1.1 Traditional AML and Sanctions Screening | 8 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.1.2 Machine Learning in Fraud Detection | 9 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.1.3 Graph Neural Networks for Financial Crime | 10 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.1.4 Large Language Models in Compliance | 11 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.1.5 Retrieval-Augmented Generation (RAG) for KYB | 12 |
| 2.2 Commercial Platforms and Their Approaches | 13 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.2.1 Sanctions Screening Platforms (Sanctions.io, Checkmarble) | 13 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.2.2 Fraud Detection Platforms (Sardine, Feedzai, SEON) | 14 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.2.3 KYB/KYC Platforms (Alloy, Persona, KYC Hub) | 15 |
| 2.3 Open-Source Foundations | 16 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.3.1 AML-MultiAgent-RAG | 16 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.3.2 Moov Watchman | 16 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.3.3 Real-Time Fraud Detection Pipelines | 17 |
| 2.4 Identification of Research Gaps | 17 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.4.1 Lack of Agentic AI in Compliance Workflows | 17 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.4.2 Fragmented Tooling (Screening ≠ Fraud ≠ KYB) | 18 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.4.3 Explainability Deficits in Black-Box Models | 18 |
| &nbsp;&nbsp;&nbsp;&nbsp;2.4.4 Limited Open-Source Production-Grade Solutions | 19 |
| 2.5 Chapter Summary | 19 |

---

### CHAPTER 3: PROBLEM STATEMENT
| Section | Page |
|---------|------|
| 3.1 Problem Description | 20 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.1.1 Transaction Screening: False Positives and Missed Matches | 20 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.1.2 Fraud Detection: Latency and Pattern Blind Spots | 21 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.1.3 Merchant Onboarding: Manual Review Bottlenecks | 21 |
| 3.2 Research Questions | 22 |
| 3.3 Objectives | 22 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.3.1 Specific Goals | 22 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.3.2 Measurable and Achievable Targets | 23 |
| 3.4 System Requirements | 23 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.4.1 Functional Requirements | 23 |
| &nbsp;&nbsp;&nbsp;&nbsp;3.4.2 Non-Functional Requirements | 24 |

---

### CHAPTER 4: METHODOLOGY
| Section | Page |
|---------|------|
| 4.1 Research Methodology | 25 |
| 4.2 System Development Methodology | 25 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.2.1 Agile Development with Phased Delivery | 25 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.2.2 Design Science Research Approach | 26 |
| 4.3 Methods and Techniques Used | 26 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.3.1 Vector Embedding-Based Entity Resolution | 26 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.3.2 Graph Neural Network (GNN) for Fraud Ring Detection | 27 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.3.3 Retrieval-Augmented Generation (RAG) for Document Processing | 27 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.3.4 Agentic AI for Alert Triage | 28 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.3.5 Hybrid Rule-Based + ML Decision Engine | 28 |
| 4.4 Tools, Technologies, and Software | 29 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.4.1 Backend: FastAPI, Python 3.11 | 29 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.4.2 Databases: PostgreSQL, Milvus, Neo4j, Redis | 29 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.4.3 AI/ML: LangChain, LlamaIndex, XGBoost, PyTorch Geometric | 30 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.4.4 Streaming: Apache Kafka, Redis Streams | 30 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.4.5 DevOps: Docker, Kubernetes, Prometheus, Grafana | 30 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.4.6 OCR: Tesseract, EasyOCR | 31 |
| 4.5 Data Collection and Analysis Procedures | 31 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.5.1 Synthetic Fraud Dataset Generation | 31 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.5.2 Public Sanctions Data (OFAC, EU, UN) | 32 |
| &nbsp;&nbsp;&nbsp;&nbsp;4.5.3 Model Evaluation Metrics | 32 |

---

### CHAPTER 5: SYSTEM DESIGN
| Section | Page |
|---------|------|
| 5.1 Architectural Design | 33 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.1.1 High-Level System Architecture | 33 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.1.2 Event-Driven Microservices Architecture | 34 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.1.3 Data Flow Architecture | 35 |
| 5.2 Module Design | 36 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.2.1 Transaction Screening Engine | 36 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.1.1 Entity Resolution Module | 36 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.1.2 Vector Fuzzy Matching Module | 37 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.1.3 LLM Contextual Analysis Module | 37 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.1.4 Audit Trail Module | 38 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.2.2 Real-Time Fraud Detection Engine | 38 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.2.1 Behavioral Profiling Module | 38 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.2.2 Graph Analysis Module | 39 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.2.3 Agentic Alert Triage Module | 39 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.2.3 Automated Merchant Approval Engine | 40 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.3.1 RAG-Powered Document Extraction | 40 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.3.2 Web Scraping & Reputation Module | 41 |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2.3.3 Dynamic Risk Scoring Module | 41 |
| 5.3 Database Design | 42 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.3.1 Entity-Relationship Diagram | 42 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.3.2 PostgreSQL Schema | 43 |
| &nbsp;&nbsp;&nbsp;&nbsp;5.3.3 Milvus Collection Schemas | 43 |
| &nbsp;&　　　　5.3.4 Neo4j Graph Schema | 44 |
| 5.4 API Design | 44 |
| &nbsp;&　　　　5.4.1 Transaction Screening API | 44 |
| &nbsp;&　　　　5.4.2 Fraud Detection API | 45 |
| &nbsp;&　　　　5.4.3 Merchant Approval API | 45 |
| 5.5 Use Case Diagrams | 46 |
| 5.6 Sequence Diagrams | 46 |
| &nbsp;&　　　　5.6.1 Transaction Screening Flow | 46 |
| &　　　　5.6.2 Fraud Alert Triage Flow | 47 |
| &　　　　5.6.3 Merchant Onboarding Flow | 47 |
| 5.7 Component Diagrams | 48 |
| 5.8 Deployment Architecture | 48 |

---

### CHAPTER 6: IMPLEMENTATION
| Section | Page |
|---------|------|
| 6.1 Implementation Environment | 49 |
| &nbsp;&　　　　6.1.1 Development Setup | 49 |
| &nbsp;&　　　　6.1.2 Docker Compose Infrastructure | 49 |
| 6.2 Phase 1: Foundation & Architecture | 50 |
| &　　　　6.2.1 FastAPI Application Skeleton | 50 |
| &　　　　6.2.2 Database Migration Scripts (Alembic) | 51 |
| &　　　　6.2.3 Shared Infrastructure Clients | 51 |
| 6.3 Phase 2: Transaction Screening Engine | 52 |
| &　　　　6.3.1 AML Rule Engine Implementation | 52 |
| &　　　　6.3.2 Vector Database Integration (Milvus) | 53 |
| &　　　　6.3.3 LLM Entity Resolution with LangChain | 53 |
| &　　　　6.3.4 Screening API Endpoint | 54 |
| 6.4 Phase 3: Real-Time Fraud Detection | 55 |
| &　　　　6.4.1 Behavioral Profiling Pipeline | 55 |
| &　　　　6.4.2 XGBoost Fraud Model Training | 56 |
| &　　　　6.4.3 Graph Analysis with Neo4j | 56 |
| &　　　　6.4.4 Agentic Alert Triage (LangGraph) | 57 |
| 6.5 Phase 4: Automated Merchant Approval | 58 |
| &　　　　6.5.1 KYB/KYC Document Pipeline | 58 |
| &　　　　6.5.2 RAG Document Extraction (LlamaIndex) | 59 |
| &　　　　6.5.3 Web Scraping & Verification Module | 59 |
| &　　　　6.5.4 Risk Scoring Engine | 60 |
| 6.6 Phase 5: Integration & Hardening | 61 |
| &　　　　6.6.1 Kafka Event Pipeline | 61 |
| &　　　　6.6.2 Cross-Module Integration | 62 |
| &　　　　6.6.3 Monitoring and Alerting | 62 |
| 6.7 Code Snippets and Explanation | 63 |
| &　　　　6.7.1 Key Implementation Snippets | 63 |
| &　　　　6.7.2 Model Training Code | 64 |
| &　　　　6.7.3 Agent Tool Definitions | 64 |
| 6.8 Snapshots and Results | 65 |
| &　　　　6.8.1 Screening Engine Output | 65 |
| &　　　　6.8.2 Fraud Detection Dashboard | 66 |
| &　　　　6.8.3 Merchant Onboarding Workflow | 66 |

---

### CHAPTER 7: TESTING
| Section | Page |
|---------|------|
| 7.1 Testing Strategies and Methodologies | 67 |
| &　　　　7.1.1 Unit Testing (pytest) | 67 |
| &　　　　7.1.2 Integration Testing | 68 |
| &　　　　7.1.3 Load Testing (Locust) | 68 |
| &　　　　7.1.4 Model Evaluation Testing | 69 |
| 7.2 Test Cases | 69 |
| &　　　　7.2.1 Transaction Screening Test Cases | 69 |
| &　　　　7.2.2 Fraud Detection Test Cases | 70 |
| &　　　　7.2.3 Merchant Approval Test Cases | 71 |
| &　　　　7.2.4 API Endpoint Test Cases | 71 |
| 7.3 Test Results | 72 |
| &　　　　7.3.1 Screening Engine Accuracy | 72 |
| &　　　　7.3.2 Fraud Model Performance | 73 |
| &　　　　7.3.3 System Latency Benchmarks | 73 |
| 7.4 Bug Fixes and Improvements | 74 |
| 7.5 Regression Testing | 74 |

---

### CHAPTER 8: RESULTS AND DISCUSSION
| Section | Page |
|---------|------|
| 8.1 Experimental Results | 75 |
| &　　　　8.1.1 Transaction Screening Results | 75 |
| &　　　　8.1.2 Fraud Detection Results | 76 |
| &　　　　8.1.3 Merchant Approval Results | 77 |
| 8.2 Performance Analysis | 78 |
| &　　　　8.2.1 Latency Analysis | 78 |
| &　　　　8.2.2 Throughput Analysis | 79 |
| &　　　　8.2.3 Resource Utilization | 79 |
| 8.3 Comparison with Existing Solutions | 80 |
| &　　　　8.3.1 Comparison with Rule-Based Systems | 80 |
| &　　　　8.3.2 Comparison with Commercial Platforms | 81 |
| 8.4 Ablation Study | 82 |
| &　　　　8.4.1 Impact of Graph Features | 82 |
| &　　　　8.4.2 Impact of LLM Contextual Analysis | 83 |
| &　　　　8.4.3 Impact of RAG Document Extraction | 83 |
| 8.5 Discussion | 84 |
| &　　　　8.5.1 Interpretation of Results | 84 |
| &　　　　8.5.2 Practical Implications | 85 |
| &　　　　8.5.3 Limitations of the Study | 85 |

---

### CHAPTER 9: CONCLUSION AND FUTURE SCOPE
| Section | Page |
|---------|------|
| 9.1 Findings and Significance | 86 |
| 9.2 Achievements and Contributions | 87 |
| &　　　　9.2.1 Technical Contributions | 87 |
| &　　　　9.2.2 Research Contributions | 88 |
| &　　　　9.2.3 Practical Contributions | 88 |
| 9.3 Future Scope | 89 |
| &　　　　9.3.1 Advanced Features | 89 |
| &　　　　9.3.2 Scalability Improvements | 90 |
| &　　　　9.3.3 Regulatory Expansion | 90 |
| &　　　　9.3.4 International Deployment | 91 |

---

### CHAPTER 10: REFERENCES
| Section | Page |
|---------|------|
| 10.1 Academic References | 92 |
| 10.2 Industry Reports | 95 |
| 10.3 Technical Documentation | 96 |
| 10.4 Open-Source Projects | 97 |

---

### APPENDICES
| Appendix | Content | Page |
|----------|---------|------|
| A | Project Source Code Repository Structure | 98 |
| B | Complete API Reference | 99 |
| C | Database Schema DDL | 102 |
| D | Docker Compose Configuration | 104 |
| E | Model Training Configuration | 106 |
| F | Sample Screening Reports | 107 |
| G | Fraud Alert Dashboard Screenshots | 109 |
| H | Merchant Onboarding Workflow Screenshots | 111 |
| I | Research Interview Guide (if applicable) | 113 |
| J | Ethics Approval and Data Privacy Statement | 114 |

---

### LIST OF TABLES
| Table No. | Table Name | Page |
|-----------|------------|------|
| 1.1 | Project Objectives and Measurable Targets | 4 |
| 2.1 | Comparison of Commercial Fraud Detection Platforms | 14 |
| 2.2 | Open-Source AML/Fraud Projects Review | 16 |
| 3.1 | Functional Requirements Specification | 23 |
| 3.2 | Non-Functional Requirements | 24 |
| 5.1 | PostgreSQL Entity Schema | 42 |
| 5.2 | Milvus Collection Schema | 43 |
| 5.3 | API Endpoint Specification | 44 |
| 6.1 | Technology Stack Summary | 29 |
| 7.1 | Unit Test Cases — Screening Engine | 69 |
| 7.2 | Unit Test Cases — Fraud Detection | 70 |
| 7.3 | Integration Test Results | 72 |
| 8.1 | Screening Engine Performance Metrics | 75 |
| 8.2 | Fraud Model Evaluation Metrics | 76 |
| 8.3 | Latency Benchmarks by Module | 78 |
| 8.4 | Comparison with Rule-Based Baseline | 80 |
| 8.5 | Ablation Study Results | 82 |

---

### LIST OF FIGURES
| Figure No. | Figure Name | Page |
|------------|-------------|------|
| 1.1 | Global AI Fraud Detection Market Growth (2024-2030) | 1 |
| 2.1 | Conceptual Framework of AI in Financial Compliance | 8 |
| 5.1 | High-Level System Architecture Diagram | 33 |
| 5.2 | Event-Driven Microservices Architecture | 34 |
| 5.3 | Data Flow Diagram — Transaction Screening | 35 |
| 5.4 | Module Interaction Diagram | 36 |
| 5.5 | Entity-Relationship Diagram | 42 |
| 5.6 | Use Case Diagram | 46 |
| 5.7 | Sequence Diagram — Transaction Screening Flow | 46 |
| 5.8 | Sequence Diagram — Fraud Alert Triage Flow | 47 |
| 5.9 | Sequence Diagram — Merchant Onboarding Flow | 47 |
| 5.10 | Deployment Architecture (Docker/Kubernetes) | 48 |
| 6.1 | AML Rule Engine Architecture | 52 |
| 6.2 | Vector Fuzzy Matching Pipeline | 53 |
| 6.3 | LLM Entity Resolution Workflow | 54 |
| 6.4 | Behavioral Profiling Pipeline | 55 |
| 6.5 | Graph Analysis Module — Fraud Ring Detection | 56 |
| 6.6 | Agentic Alert Triage Agent Architecture | 57 |
| 6.7 | RAG Document Extraction Pipeline | 59 |
| 6.8 | Risk Scoring Engine Flow | 60 |
| 6.9 | Kafka Event Pipeline Architecture | 61 |
| 7.1 | Testing Framework Architecture | 67 |
| 8.1 | Screening Recall vs Precision Curve | 75 |
| 8.2 | Fraud Detection ROC Curve | 76 |
| 8.3 | Merchant Onboarding Time Distribution | 77 |
| 8.4 | System Throughput Under Load | 79 |
| 8.5 | Component Performance Comparison | 81 |

---

### LIST OF ABBREVIATIONS
| Abbreviation | Full Form |
|--------------|-----------|
| AML | Anti-Money Laundering |
| KYC | Know Your Customer |
| KYB | Know Your Business |
| KYD | Know Your Director |
| PEP | Politically Exposed Person |
| UBO | Ultimate Beneficial Owner |
| LLM | Large Language Model |
| RAG | Retrieval-Augmented Generation |
| GNN | Graph Neural Network |
| API | Application Programming Interface |
| REST | Representational State Transfer |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| AUC-ROC | Area Under Curve - Receiver Operating Characteristic |
| OFAC | Office of Foreign Assets Control |
| FATF | Financial Action Task Force |
| SAR | Suspicious Activity Report |
| CTR | Currency Transaction Report |
| ML | Machine Learning |
| DL | Deep Learning |
| NLP | Natural Language Processing |
| NER | Named Entity Recognition |
| DB | Database |
| CPU | Central Processing Unit |
| GPU | Graphics Processing Unit |
| CI/CD | Continuous Integration / Continuous Deployment |
| SaaS | Software as a Service |
| UML | Unified Modeling Language |
| ER | Entity-Relationship |
| SLA | Service Level Agreement |
| DevOps | Development Operations |
| ORM | Object-Relational Mapping |
| HTTP | HyperText Transfer Protocol |
| HTTPS | HyperText Transfer Protocol Secure |
| K8s | Kubernetes |
| Docker | Platform for containerized application development |
| Kafka | Distributed event streaming platform |
| SQL | Structured Query Language |
| NoSQL | Non-relational database |
| ONNX | Open Neural Network Exchange |
| MLOps | Machine Learning Operations |
| F1 | F1-Score (harmonic mean of precision and recall) |
| SMOTE | Synthetic Minority Over-sampling Technique |
| SHAP | SHapley Additive exPlanations |
| UBA | User Behavior Analytics |
| TPS | Transactions Per Second |
| P99 | 99th percentile latency |

---

*Table of Contents — Sentinel: AI-Powered Transaction Screening, Fraud Detection, and Merchant Approval*
*Major Project-I, B.Tech CSE-AIML, IPS Academy, Indore, RGPV University, 2026-27*
