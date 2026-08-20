# CHAPTER 4: METHODOLOGY

## 4.1 Research Methodology

This project employs **Design Science Research** (Peffers et al., 2007), an iterative methodology for building and evaluating artificial artifacts that solve identified problems. The research cycle consists of:

1. **Problem Identification**: Literature review and market analysis to identify gaps in compliance technology
2. **Objective Definition**: Establishing measurable targets for the artifact
3. **Design & Development**: Building the Sentinel platform through iterative sprints
4. **Evaluation**: Testing against defined metrics (recall, precision, latency, coverage)
5. **Communication**: Documenting findings in this report and open-source repository

## 4.2 System Development Methodology

### 4.2.1 Agile Development with Phased Delivery
The project follows a 5-phase Agile methodology, with each phase delivering a verifiable increment:

- **Phase 1 (Weeks 1-4)**: Foundation — infrastructure, database schema, core services
- **Phase 2 (Weeks 5-8)**: Screening Engine — AML rules, entity resolution
- **Phase 3 (Weeks 9-12)**: Fraud Detection — behavioral profiling, ML models
- **Phase 4 (Weeks 13-16)**: Merchant Approval — KYB pipeline, risk scoring
- **Phase 5 (Weeks 17-20)**: Integration — event pipeline, monitoring, documentation

Each phase includes design, implementation, testing, and review activities.

### 4.2.2 Test-Driven Development (TDD)
All modules follow TDD principles:
1. Write failing tests before implementation
2. Implement minimal code to pass tests
3. Refactor while maintaining test coverage
4. Target: >40% code coverage (achieved: 52%)

## 4.3 Methods and Techniques Used

### 4.3.1 Vector Embedding-Based Entity Resolution
Entity resolution matches transaction parties against sanctions lists despite name variations. The approach uses:

1. **Sentence Transformers**: Encode entity names into 384-dimensional vectors using `all-MiniLM-L6-v2`
2. **Milvus Vector DB**: Store embeddings with hybrid search (vector + metadata + full-text)
3. **Cosine Similarity**: Compute similarity scores between query and candidate embeddings
4. **Threshold-Based Alerting**: Flag matches above configurable similarity threshold (default: 0.5)

The system falls back to hash-based placeholder embeddings when sentence-transformers is unavailable.

### 4.3.2 Graph Neural Networks for Fraud Ring Detection
Graph analysis maps relationships between accounts to detect coordinated fraud:

1. **Neo4j Graph Database**: Store entities as nodes, relationships as directed edges
2. **Cypher Queries**: Detect shared attributes (device, IP, phone) across accounts
3. **Community Detection**: Identify fraud rings using connected component analysis
4. **Multi-Hop Traversal**: Find entities within N hops of a seed account

The graph module supports fraud ring detection with depth-2 traversal by default.

### 4.3.3 Retrieval-Augmented Generation (RAG) for Document Processing
RAG pipelines extract information from merchant documents:

1. **Document Ingestion**: PDF/image parsing with PyMuPDF and Tesseract/EasyOCR
2. **Text Chunking**: Split documents into semantically coherent chunks
3. **Embedding Generation**: Convert chunks to vectors using sentence transformers
4. **Vector Storage**: Store in Milvus for similarity search
5. **LLM Extraction**: Use function calling to extract structured fields (business name, registration number, address)

### 4.3.4 Agentic AI for Alert Triage
The triage agent investigates fraud alerts autonomously:

1. **Tool-Use Pattern**: Agent calls tools to query databases, retrieve profiles, check graph
2. **Multi-Source Correlation**: Combines PostgreSQL (transactions), Redis (profiles), Neo4j (graphs)
3. **Reasoning Chain**: Agent synthesizes findings into a risk dossier
4. **Recommendation**: Agent outputs ESCALATE/INVESTIGATE/DISMISS with confidence score

### 4.3.5 Hybrid Decision Engine
Sentinel combines deterministic and probabilistic approaches:

| Layer | Type | Examples |
|-------|------|----------|
| Rule Engine | Deterministic | Amount threshold, jurisdiction check |
| Behavioral | Statistical | Z-score, velocity, geo-impossibility |
| ML Model | Probabilistic | XGBoost fraud classifier |
| Graph | Relational | Fraud ring detection, shared attributes |
| LLM | Semantic | Entity resolution, document extraction |

The final recommendation is a weighted ensemble of all layers.

## 4.4 Tools, Technologies, and Software

### 4.4.1 Backend Framework
- **FastAPI**: Async web framework with automatic OpenAPI documentation
- **Pydantic v2**: Data validation and settings management
- **Uvicorn**: ASGI server for production deployment

### 4.4.2 Data Storage
| Component | Technology | Purpose |
|-----------|------------|---------|
| Relational DB | PostgreSQL 16 | Transaction metadata, user profiles, audit logs |
| Vector DB | Milvus 2.4 | Entity embeddings, fuzzy matching |
| Graph DB | Neo4j 5.22 | Fraud ring detection, relationship analysis |
| Cache | Redis 7 | Hot feature store, session state, rate limiting |
| Search | pgvector | Lightweight vector search (dev) |

### 4.4.3 AI/ML Stack
| Component | Technology | Purpose |
|-----------|------------|---------|
| LLM Orchestration | LangChain | Agent workflows, RAG pipelines |
| Document Retrieval | LlamaIndex | RAG over compliance documents |
| Embeddings | sentence-transformers | Entity name vectorization |
| ML Training | XGBoost, scikit-learn | Fraud classification |
| Graph ML | PyTorch Geometric | GNN-based fraud detection |

### 4.4.4 Event Streaming
| Component | Technology | Purpose |
|-----------|------------|---------|
| Message Broker | Apache Kafka | Transaction event pipeline |
| In-Memory Queue | Redis Streams | Low-latency event buffering |
| Schema Registry | Confluent Schema Registry | Event schema validation |

### 4.4.5 DevOps
| Component | Technology | Purpose |
|-----------|------------|---------|
| Containerization | Docker + Compose | Local development, CI |
| Orchestration | Kubernetes | Production deployment |
| Monitoring | Prometheus + Grafana | Metrics, alerting |
| CI/CD | GitHub Actions | Build, test, deploy |

### 4.4.6 Document Processing
| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Parsing | PyMuPDF | Document text extraction |
| OCR (Fast) | Tesseract | Clean printed documents |
| OCR (Accurate) | EasyOCR | Complex/handwritten docs |
| Web Scraping | Playwright, BeautifulSoup | Merchant reputation data |

## 4.5 Data Collection and Analysis Procedures

### 4.5.1 Synthetic Fraud Dataset Generation
Due to data privacy constraints, a synthetic dataset was generated:

1. **Legitimate Transactions**: 900 transactions with normal distributions (mean=$150, std=$50)
2. **Fraudulent Transactions**: 100 transactions with anomalous patterns:
   - High amounts ($5,000-$50,000)
   - High velocity (5+ transactions/hour)
   - Geographic impossibility
   - Round-trip patterns
3. **Feature Engineering**: Amount, z-score, velocity, geo-anomaly, time-anomaly
4. **Train/Test Split**: 80/20 stratified split

### 4.5.2 Model Evaluation Metrics
| Metric | Formula | Target |
|--------|---------|--------|
| Accuracy | (TP+TN)/(TP+TN+FP+FN) | >90% |
| Precision | TP/(TP+FP) | >85% |
| Recall | TP/(TP+FN) | >95% |
| F1-Score | 2×Precision×Recall/(Precision+Recall) | >90% |
| AUC-ROC | Area under ROC curve | >0.90 |
| False Positive Rate | FP/(FP+TN) | <10% |

### 4.5.3 Performance Benchmarking
System performance was measured using:
- **Locust**: Load testing for API endpoints
- **pytest-benchmark**: Unit test performance
- **Prometheus**: Production metrics collection
- **Custom latency trackers**: p50, p95, p99 response times
