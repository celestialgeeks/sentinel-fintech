# Sentinel FinTech — Code Review Report (Phase 1)
**Reviewer:** Agnes (Code Reviewer Subagent)  
**Date:** August 20, 2026  
**Scope:** Phase 1 Foundation & Architecture (scaffold + documentation)  
**Status:** Project in early Phase 1 — `src/` and `tests/` directories are empty

---

## Executive Summary

The Sentinel FinTech project has a solid architectural foundation with well-thought-out documentation, research, and infrastructure scaffolding. However, several **critical security issues** exist in the docker-compose.yml and .env.example that must be addressed before any code is written. The project structure is well-designed for the microservices pattern, but implementation details will need rigorous review as Phase 1 code is produced.

**Overall Phase 1 Readiness: ⚠️ NEEDS FIXES BEFORE PROCEEDING**

---

## 1. SECURITY FINDINGS

### 🔴 CRITICAL: Hardcoded Credentials in docker-compose.yml

**File:** `docker-compose.yml`, **Lines:** 43-44, 66, 102-103, 176

```yaml
# Line 43-44 — PostgreSQL password hardcoded
- POSTGRES_PASSWORD=sentinel_pass

# Line 66 — Redis password hardcoded  
command: redis-server --appendonly yes --requirepass sentinel_redis_pass

# Line 102-103 — MinIO credentials hardcoded
- MINIO_ROOT_USER=minioadmin
- MINIO_ROOT_PASSWORD=minioadmin

# Line 176 — Grafana password with weak default
- GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
```

**Risk:** These credentials are committed to version control. Anyone with repo access can connect to all services. In a fintech context, this is unacceptable.

**Fix:**
```yaml
# Use Docker secrets or external secret management
postgres:
  environment:
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  secrets:
    - postgres_password

secrets:
  postgres_password:
    env: POSTGRES_PASSWORD
```

Also update `.env.example` to use placeholder values and document that real credentials must be generated per environment.

---

### 🔴 CRITICAL: Weak Default JWT Secret

**File:** `.env.example`, **Line:** 23

```
JWT_SECRET=change-this-to-a-secure-random-string
```

**Risk:** The placeholder is descriptive but not a real secret. If a developer forgets to replace it and deploys to production with this value, all JWT validation is bypassed.

**Fix:**
```bash
# Generate a proper secret:
# python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=
JWT_SECRET_DESCRIPTION=Generate with: python -c "import secrets; print(secrets.token_hex(32))"
```

Add validation in application startup to fail fast if JWT_SECRET is too short or contains the placeholder text.

---

### 🟡 ISSUE: Insecure Redis Connection String in .env.example

**File:** `.env.example`, **Line:** 12

```
REDIS_URL=redis://:sentinel_redis_pass@redis:6379/0
```

**Risk:** The password `sentinel_redis_pass` is a weak, predictable string. Also, Redis is exposed on port 6379 without TLS.

**Fix:**
```bash
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
# In production, enable TLS:
# REDIS_URL=rediss://:${REDIS_PASSWORD}@redis:6379/0
```

Add to docker-compose.yml:
```yaml
redis:
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --tls-port 6380
```

---

### 🟡 ISSUE: Missing Input Validation Documentation

**File:** `README.md`, **Lines:** 186-195 (API endpoints)

The documented API endpoints lack any mention of input validation requirements. For a fintech system handling financial transactions, this is a significant gap.

**Fix:** Add to each endpoint documentation:
```markdown
| Method | Path | Description | Input Validation |
|--------|------|-------------|------------------|
| `POST` | `/api/v1/screening/transactions` | Submit transaction | Amount > 0, valid currency code (ISO 4217), required fields: sender, receiver, amount |
```

---

### 🟡 ISSUE: No Rate Limiting Implementation Plan

**File:** `docs/IMPLEMENTATION_PLAN.md`, **Phase 1, Milestone 1.4**

The plan mentions "Rate limiting (Redis-backed)" but doesn't specify:
- Rate limits per endpoint
- Burst vs. sustained limits
- Authentication vs. anonymous limits
- Response headers (Retry-After)

**Fix:** Add to implementation plan:
```markdown
- [ ] Implement rate limiting middleware with Redis sliding window
- [ ] Configure limits: 100 req/min for authenticated, 20 req/min for anonymous
- [ ] Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After)
- [ ] Document rate limits in API spec
```

---

### 🟡 ISSUE: CORS Configuration Missing from Plan

**File:** `docs/IMPLEMENTATION_PLAN.md`, **Phase 1, Milestone 1.4**

CORS is mentioned but no specific configuration is planned. For a fintech app, CORS must be strictly configured.

**Fix:** Add to implementation plan:
```markdown
- [ ] Configure CORS with explicit allowed origins (not wildcard *)
- [ ] Disable credentials mode unless explicitly needed
- [ ] Add CORS preflight caching
- [ ] Document CORS policy in API reference
```

---

### 🟢 PASS: .gitignore Properly Excludes .env

**File:** `.gitignore`, **Lines:** 48-51

```
# ─── Environment variables ─────────────────────────────────
.env
.env.local
.env.*.local
```

This is correctly configured to prevent accidental secret commits.

---

### 🟢 PASS: Dockerfile Uses Non-Root User

**File:** `Dockerfile`, **Lines:** 20-21

```dockerfile
RUN useradd -m -u 1000 sentinel
USER sentinel
```

Good security practice — the application runs as a non-root user.

---

## 2. CODE QUALITY FINDINGS

### 🟢 PASS: requirements.txt Uses Pinned Versions

**File:** `requirements.txt`

All dependencies use exact version pins (e.g., `fastapi==0.115.0`). This ensures reproducible builds.

### 🟡 ISSUE: Duplicate Dependency

**File:** `requirements.txt`, **Lines:** 47 and 66

```
httpx==0.27.2    # Line 47 (web scraping)
httpx==0.27.2    # Line 66 (testing)
```

`httpx` is listed twice. While pip handles duplicates gracefully, this is messy and should be consolidated.

**Fix:** Remove the duplicate and add a comment if needed:
```
httpx==0.27.2            # HTTP client (web scraping + testing)
```

---

### 🟡 ISSUE: Missing pyproject.toml

**File:** Root directory

The project uses `requirements.txt` but has no `pyproject.toml` or `setup.py`. This means:
- No tool configuration (pytest, mypy, ruff, black, etc.)
- No dependency groups (dev, test, production)
- No package metadata

**Fix:** Create `pyproject.toml`:
```toml
[project]
name = "sentinel-fintech"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # ... from requirements.txt ...
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "pytest-cov", "ruff", "mypy"]
ml = ["torch", "xgboost", "scikit-learn"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
```

---

### 🟢 PASS: README.md Has Clear Architecture Documentation

The README provides a comprehensive overview including:
- Tech stack table
- Architecture diagram (ASCII)
- API endpoint table
- Development phases
- Quick start instructions

This is excellent documentation for a new contributor.

---

## 3. ARCHITECTURE FINDINGS

### 🟢 PASS: Microservices Pattern Properly Separated

**File:** `docs/IMPLEMENTATION_PLAN.md`

The planned architecture correctly separates:
- Screening Engine (AML/sanctions)
- Fraud Detection Engine (behavioral + graph ML)
- Merchant Approval Engine (KYB/KYC)
- Shared infrastructure (DB, cache, streaming)

Each engine has its own module space (`src/screening/`, `src/fraud/`, `src/merchant/`) which enforces separation of concerns.

### 🟡 ISSUE: No Schema Registry Plan for Kafka

**File:** `docs/IMPLEMENTATION_PLAN.md`, **Phase 5, Milestone 5.1**

Kafka event schemas are planned but there's no schema registry strategy. For a fintech system with multiple services producing/consuming events, schema evolution is critical.

**Fix:** Add to Phase 2 or Phase 5:
```markdown
- [ ] Implement JSON Schema or Avro schema registry for Kafka events
- [ ] Define schemas: TransactionEvent, ScreeningResult, FraudAlert, MerchantOnboarding
- [ ] Add schema validation in producers and consumers
- [ ] Plan for schema evolution (forward/backward compatibility)
```

### 🟡 ISSUE: Graph Database Choice Inconsistent

**File:** `docs/IMPLEMENTATION_PLAN.md` vs `docker-compose.yml`

- **Implementation Plan** (line 113) recommends Neo4j for graph storage
- **Docker Compose** does not include Neo4j
- **Research Report** mentions Neo4j as primary graph DB

This inconsistency will cause confusion. The project should decide:
1. Use PostgreSQL with pg_graphql extension (simpler, fewer services)
2. Add Neo4j to docker-compose (more features, more complexity)

**Recommendation:** For Phase 1-3, use PostgreSQL with `ltree` extension for hierarchical queries. Add Neo4j in Phase 3 if graph complexity requires it.

### 🟢 PASS: Event-Driven Architecture with Kafka

The planned Kafka topology (`transactions.raw`, `transactions.scrubbed`, `fraud.alerts`, `merchant.onboarding`) is well-designed for decoupling and scalability.

### 🟢 PASS: Vector Database Integration Planned

Milvus integration for entity resolution and fuzzy matching is appropriate for the use case. The hybrid search approach (vector + metadata + full-text) is industry best practice.

---

## 4. TESTING FINDINGS

### 🔴 CRITICAL: No Tests Exist

**Files:** `tests/` directory is empty

For a fintech application, the complete absence of tests is a critical risk. Financial systems require:
- Unit tests for all business logic
- Integration tests for API endpoints
- Security tests for authentication/authorization
- Performance tests for latency-sensitive operations

**Fix:** Before proceeding with Phase 1 code, create test scaffolding:
```bash
# Create test structure
mkdir -p tests/api tests/screening tests/fraud tests/merchant tests/shared

# Create conftest.py for fixtures
touch tests/conftest.py
touch tests/api/test_health.py
```

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

---

### 🟡 ISSUE: No Test Coverage Target Defined

**File:** `pyproject.toml` (missing)

There's no coverage requirement or target defined.

**Fix:** Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

---

### 🟡 ISSUE: No Database Test Fixtures Planned

The implementation plan doesn't mention test fixtures for PostgreSQL, Redis, or Milvus.

**Fix:** Add to Phase 1 Milestone 1.4:
```markdown
- [ ] Create pytest fixtures for database connections (using testcontainers or docker-compose fixtures)
- [ ] Create Redis test client fixture
- [ ] Create Milvus test collection fixture
- [ ] Implement transactional test pattern (rollback after each test)
```

---

## 5. PERFORMANCE FINDINGS

### 🟢 PASS: Async Database Driver Selected

**File:** `requirements.txt`, **Line:** 10

```
asyncpg==0.29.0
```

`asyncpg` is the fastest PostgreSQL driver for Python and supports connection pooling natively. This is the right choice for an async FastAPI application.

### 🟢 PASS: Redis for Caching and Rate Limiting

The plan correctly uses Redis for:
- Caching (hot data)
- Rate limiting (sliding window)
- Message brokering (Redis Streams as fallback)

### 🟡 ISSUE: No Connection Pool Configuration Documented

**File:** `docker-compose.yml`, **Line:** 14

```yaml
- REDIS_URL=redis://redis:6379/0
```

No pool size or timeout configuration is specified. For a production system handling 1000s of requests/second, connection pool configuration is critical.

**Fix:** Add to `.env.example`:
```bash
# PostgreSQL
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# Redis
REDIS_POOL_SIZE=50
REDIS_CONNECTION_TIMEOUT=5
```

### 🟡 ISSUE: No Load Testing Plan

**File:** `docs/IMPLEMENTATION_PLAN.md`

While `locust` is in `requirements.txt`, there's no load testing milestone in the implementation plan.

**Fix:** Add to Phase 5:
```markdown
### Milestone 5.5 — Load Testing (Week 20, additional)
- [ ] Create Locust load tests for critical endpoints
- [ ] Benchmark: 100 concurrent users, 1000 RPS
- [ ] Measure p99 latency for screening endpoint
- [ ] Identify bottlenecks (DB queries, external API calls)
- [ ] Document performance baseline
```

---

## 6. SECURITY - DETAILED CHECKLIST

### SQL Injection Prevention
**Status:** Not yet implemented (no code exists)

**Recommendations for Phase 1 implementation:**
1. Use SQLAlchemy ORM with async session (prevents raw SQL)
2. If raw SQL is needed, use parameterized queries
3. Never concatenate user input into SQL strings
4. Add SQLAlchemy audit logging in development

### JWT Validation
**Status:** Not yet implemented

**Recommendations:**
1. Use `python-jose` with explicit algorithm validation (HS256 only, not "none")
2. Validate token expiration on every request
3. Implement token refresh mechanism
4. Add JWT blacklist for logout (Redis set)
5. Use short-lived access tokens (15 min) + long-lived refresh tokens (7 days)

### Input Validation
**Status:** Not yet implemented

**Recommendations:**
1. Use Pydantic v2 models for all request/response schemas
2. Add validation for:
   - Transaction amounts (positive, max limits)
   - Currency codes (ISO 4217)
   - Email addresses (RFC 5322)
   - Phone numbers (E.164 format)
3. Add request size limits (middleware)
4. Implement validation for file uploads (MIME type, size, extension)

### Rate Limiting
**Status:** Not yet implemented

**Recommendations:**
1. Use `slowapi` or custom Redis-backed rate limiter
2. Different limits for:
   - Authenticated users: 100 req/min
   - Anonymous users: 20 req/min
   - Specific endpoints (e.g., login): 5 req/min
3. Return proper HTTP 429 responses with Retry-After header

### CORS Configuration
**Status:** Not yet implemented

**Recommendations:**
1. Never use `Allow-Origin: *` in production
2. Configure explicit allowed origins from environment
3. Enable `Allow-Credentials` only when needed
4. Add CORS preflight caching (Access-Control-Max-Age)

---

## 7. RECOMMENDED IMMEDIATE ACTIONS

### Before Writing Any Code (Phase 1 Milestone 1.1-1.2)

1. **🔴 CRITICAL:** Fix hardcoded credentials in docker-compose.yml
2. **🔴 CRITICAL:** Generate proper JWT secret and update .env.example
3. **🔴 CRITICAL:** Create test directory structure and conftest.py
4. **🟡 HIGH:** Add pyproject.toml with tool configuration
5. **🟡 HIGH:** Remove duplicate httpx dependency
6. **🟡 MEDIUM:** Document input validation requirements for each endpoint
7. **🟡 MEDIUM:** Decide on graph database strategy (PostgreSQL vs Neo4j)
8. **🟢 LOW:** Add connection pool configuration to .env.example

### Before Phase 2 (Screening Engine)

1. Implement base FastAPI application with:
   - Health check endpoint
   - JWT authentication middleware
   - CORS middleware
   - Rate limiting middleware
   - Structured logging
2. Create database models and Alembic migrations
3. Write integration tests for health endpoint
4. Set up CI pipeline with GitHub Actions

---

## 8. FILE-SPECIFIC REVIEW

### docker-compose.yml
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 43-44 | Hardcoded PostgreSQL password | CRITICAL | Use env var or Docker secrets |
| 66 | Hardcoded Redis password | CRITICAL | Use env var |
| 102-103 | Hardcoded MinIO credentials | HIGH | Use env var |
| 176 | Weak default Grafana password | MEDIUM | Require explicit password |
| 13-17 | Missing env var references | LOW | Use `${VAR:-default}` pattern |

### Dockerfile
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 6-9 | Installs gcc/g++ (needed for psycopg2) | INFO | Consider using `psycopg[c]` instead |
| 20-21 | Non-root user created | PASS | Good practice |
| 16 | Copies src before installing deps | LOW | Already correct (COPY requirements.txt first) |

### .env.example
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 7 | Placeholder password in DATABASE_URL | HIGH | Remove example password, document generation |
| 12 | Weak Redis password | HIGH | Use placeholder, document generation |
| 23 | Descriptive but insecure JWT_SECRET | CRITICAL | Add generation command |
| 38 | Weak default Grafana password | MEDIUM | Remove default |

### requirements.txt
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 47,66 | Duplicate httpx dependency | LOW | Remove duplicate |
| 23-24 | Both kafka-python and confluent-kafka | INFO | Choose one (confluent-kafka is faster) |

### README.md
| Line | Issue | Severity | Fix |
|------|-------|----------|-----|
| 90-91 | GitHub repo URL (placeholder) | INFO | Update with real repo URL |
| 186-195 | API endpoints lack validation docs | MEDIUM | Add input validation column |

---

## 9. PHASE 1 IMPLEMENTATION CHECKLIST

Based on the review, here's what should be implemented in Phase 1 with security best practices:

### Week 1: Project Setup
- [x] Git repository initialized
- [x] .env.example created
- [x] requirements.txt created
- [x] README.md created
- [ ] **FIX:** Add pyproject.toml with tool config
- [ ] **FIX:** Remove duplicate httpx dependency
- [ ] **CREATE:** tests/conftest.py with base fixtures

### Week 2: Containerised Infrastructure
- [x] Dockerfile created
- [x] docker-compose.yml created
- [ ] **FIX:** Replace hardcoded credentials with env vars
- [ ] **FIX:** Add Docker secrets for sensitive values
- [ ] **CREATE:** config/database.yml
- [ ] **CREATE:** config/kafka.yml
- [ ] **CREATE:** config/milvus.yml
- [ ] **CREATE:** config/init.sql (database schema)

### Week 3: Database Schema
- [ ] **CREATE:** src/shared/models.py (SQLAlchemy models)
- [ ] **CREATE:** alembic/ directory with migrations
- [ ] **CREATE:** src/shared/db.py (async session factory)
- [ ] **CREATE:** tests/fixtures/database.py
- [ ] **TEST:** Verify schema creates correctly

### Week 4: Core FastAPI Skeleton
- [ ] **CREATE:** src/api/main.py
- [ ] **CREATE:** src/api/middleware/cors.py
- [ ] **CREATE:** src/api/middleware/auth.py
- [ ] **CREATE:** src/api/middleware/rate_limit.py
- [ ] **CREATE:** src/shared/cache.py (Redis client)
- [ ] **CREATE:** src/shared/logging.py (structured logging)
- [ ] **CREATE:** tests/api/test_health.py
- [ ] **TEST:** Verify all middleware works

---

## 10. CONCLUSION

The Sentinel FinTech project has excellent architectural planning and documentation. The research is thorough, the tech stack is well-chosen, and the phased approach is sensible.

**However, three critical security issues must be fixed before any application code is written:**

1. Hardcoded credentials in docker-compose.yml
2. Weak JWT secret placeholder in .env.example
3. No test infrastructure exists

Once these are addressed, the project is well-positioned for successful Phase 1 implementation. The microservices architecture, async patterns, and monitoring setup are all industry-standard choices for a fintech platform.

**Recommendation:** Fix the critical security issues, create the test scaffolding, and then proceed with Phase 1 implementation. Each milestone should include corresponding tests before completion.

---

*Review completed by Agnes (Code Reviewer Subagent)*  
*Hermes Agent — Nous Research*
