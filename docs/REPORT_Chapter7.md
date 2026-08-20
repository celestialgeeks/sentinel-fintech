# CHAPTER 7: TESTING

## 7.1 Testing Strategies and Methodologies

### 7.1.1 Unit Testing
Unit tests verify individual components in isolation:
- **Screening Rules**: 10 tests covering each AML rule (amount, structuring, jurisdiction, velocity, round-trip)
- **Behavioral Profiling**: 6 tests for z-score, velocity, geo, and time checks
- **KYB Verification**: 6 tests for document extraction and risk scoring
- **Alert Triage**: 4 tests for agent recommendations

### 7.1.2 Integration Testing
Integration tests verify component interactions:
- **Screening Engine**: 6 end-to-end tests from transaction ingest to recommendation
- **Fraud Scorer**: 4 tests combining behavioral + ML scoring
- **API Endpoints**: 4 tests validating HTTP request/response cycles

### 7.1.3 Test Infrastructure
```python
# Test fixtures (from tests/conftest.py)
@pytest_asyncio.fixture
async def test_engine():           # In-memory SQLite for DB tests
@pytest_asyncio.fixture
async def db_session():           # Per-test transactional session
@pytest_asyncio.fixture
async def mock_redis():           # In-memory Redis mock
@pytest_asyncio.fixture
async def mock_milvus():          # In-memory Milvus mock
@pytest_asyncio.fixture
async def mock_kafka_producer():  # MagicMock Kafka producer
@pytest_asyncio.fixture
async def mock_neo4j():           # In-memory Neo4j mock
@pytest_asyncio.fixture
async def client():               # FastAPI TestClient with patched deps
```

### 7.1.4 Testing Framework
- **pytest 8.3.2**: Test discovery and execution
- **pytest-asyncio 0.24.0**: Async test support
- **pytest-cov 5.0.0**: Coverage reporting
- **pytest-mock 3.14.0**: Mocking utilities
- **httpx 0.27.2**: Async HTTP client for TestClient

## 7.2 Test Cases

### 7.2.1 Transaction Screening Test Cases
| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| TS-001 | Normal transaction | $500, US→GB | APPROVE, score<0.4 |
| TS-002 | High amount | $50,000, US→US | amount_threshold flag |
| TS-003 | Sanctioned country | $5,000, US→BY | BLOCK or REVIEW |
| TS-004 | Watchlist match | Tech Imports LLC | matched_entities |
| TS-005 | Round-trip | usr_123→usr_123 | round_trip flag |
| TS-006 | Structuring | 4×$8,500 txns | structuring flag |

### 7.2.2 Fraud Detection Test Cases
| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| FD-001 | Normal behavior | $150, US | APPROVE |
| FD-002 | Amount anomaly | $50,000 after $100 baseline | z_score>2.0 |
| FD-003 | Velocity anomaly | 8 txns in 35 min | velocity_score>0 |
| FD-004 | New user | Single transaction | No anomalies |
| FD-005 | All recommendations | Various inputs | APPROVE/VERIFY/BLOCK |

### 7.2.3 Merchant Approval Test Cases
| Test ID | Description | Input | Expected Output |
|---------|-------------|-------|-----------------|
| MA-001 | Clean document | Full details, US, Tech | APPROVE |
| MA-002 | Missing fields | No reg number | REJECT |
| MA-003 | High-risk country | IR, Crypto | REJECT |
| MA-004 | Medium risk | US, E-commerce | REVIEW or APPROVE |
| MA-005 | Component breakdown | All inputs | 5 components |
| MA-006 | Risk score range | Various | 0.0-1.0 |

### 7.2.4 API Endpoint Test Cases
| Test ID | Endpoint | Method | Expected |
|---------|----------|--------|----------|
| AP-001 | /health | GET | 200, {"status": "ok"} |
| AP-002 | /openapi.json | GET | 200, schema |
| AP-003 | /api/v1/fraud/check | POST | 200, FraudScore |
| AP-004 | /api/v1/fraud/alerts | GET | 200, list |
| AP-005 | /api/v1/fraud/alerts/{id}/triage | POST | 404 for invalid |

## 7.3 Test Results

### 7.3.1 Unit Test Results
```
tests/test_screening_rules.py (10 tests)
  test_amount_threshold_below          PASSED
  test_amount_threshold_above          PASSED
  test_high_risk_jurisdiction          PASSED
  test_no_high_risk_jurisdiction       PASSED
  test_round_trip                      PASSED
  test_no_round_trip                   PASSED
  test_structuring_detection           PASSED
  test_velocity_detection              PASSED
  test_rule_engine_aggregation         PASSED
  test_full_engine_no_trigger          PASSED

tests/test_fraud_behavioral.py (6 tests)
  test_amount_z_score_normal           PASSED
  test_amount_z_score_anomaly          PASSED
  test_velocity_check_normal           PASSED
  test_velocity_check_anomaly          PASSED
  test_geo_impossibility_new_user      PASSED
  test_time_anomaly_new_user           PASSED

tests/test_merchant_kyb.py (6 tests)
  test_kyb_verify_clean_document       PASSED
  test_kyb_verify_missing_fields       PASSED
  test_risk_scorer_low_risk            PASSED
  test_risk_scorer_high_risk           PASSED
  test_risk_scorer_medium_risk         PASSED
  test_risk_components_breakdown       PASSED

tests/test_alert_triage.py (4 tests)
  test_triage_dismiss_low_severity     PASSED
  test_triage_escalate_high_severity   PASSED
  test_triage_investigate_medium       PASSED
  test_triage_report_structure         PASSED
```

### 7.3.2 Integration Test Results
```
tests/test_screening_integration.py (6 tests) — 6 PASSED
tests/test_fraud_scorer.py (4 tests) — 4 PASSED
tests/test_fraud_router.py (4 tests) — 4 PASSED
tests/test_health.py (2 tests) — 2 PASSED

Total: 42 passed, 0 failed
```

### 7.3.3 Coverage Report
```
Name                          Stmts   Miss  Cover
-----------------------------------------------------------
src/screening/engine.py         45      0   100%
src/screening/rules.py         106      2    98%
src/screening/schemas.py        39      1    97%
src/screening/watchlists.py     31      4    87%
src/fraud/behavioral.py         73      9    88%
src/fraud/model.py              40      4    90%
src/fraud/scorer.py             40      4    90%
src/fraud/schemas.py            45      0   100%
src/merchant/kyb.py            118     18    85%
src/merchant/risk_scoring.py    48      2    96%
src/api/main.py                 39     19    51%
src/shared/cache.py             59     22    63%
src/shared/db.py                52     20    62%
-----------------------------------------------------------
TOTAL                        1409    670    52%
```

## 7.4 Bug Fixes and Improvements

### 7.4.1 Issues Found and Fixed
1. **DateTime Deprecation**: `datetime.utcnow()` deprecated in Python 3.12 → replaced with `datetime.now(timezone.utc)`
2. **Kafka Import**: `confluent_kafka` not installed in test env → added graceful fallback
3. **Milvus Mock**: Type mismatch in test fixtures → added `type: ignore` comments
4. **XGBoost Warning**: `use_label_encoder` deprecated → removed from constructor
5. **Router Prefix**: Double-prefix issue (router + include_router) → removed router-level prefix
6. **Test Coverage**: Initially 24% → improved to 52% with additional tests

### 7.4.2 Test Improvements
- Added integration tests for end-to-end screening flow
- Added API router tests for all endpoints
- Added mock fixtures for all external services
- Fixed assertion mismatches for scoring thresholds

## 7.5 Regression Testing
All 42 tests pass consistently across multiple runs. The test suite is deterministic with seeded synthetic data generation (numpy seed=42).
