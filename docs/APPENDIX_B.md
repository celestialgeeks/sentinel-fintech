# APPENDIX B: COMPLETE API REFERENCE

## Base URL
```
http://localhost:8000/api/v1
```

## Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "ok",
  "service": "sentinel-api"
}
```

## OpenAPI Schema
```http
GET /openapi.json
GET /docs
GET /redoc
```

---

## Transaction Screening

### Submit Transaction for Screening
```http
POST /screening/transactions
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction_id": "tx_987654321",
  "timestamp": "2026-08-21T10:30:00Z",
  "amount": 15000.00,
  "currency": "USD",
  "sender": {
    "entity_id": "usr_123",
    "name": "Global Trade Corp",
    "country": "AE"
  },
  "receiver": {
    "entity_id": "merch_456",
    "name": "Tech Imports LLC",
    "country": "US"
  },
  "metadata": {
    "ip_address": "192.168.1.50",
    "device_fingerprint": "dev_abc123"
  }
}
```

**Response (200 OK):**
```json
{
  "transaction_id": "tx_987654321",
  "risk_score": 0.80,
  "flags": ["amount_threshold", "high_risk_jurisdiction"],
  "matched_entities": [
    {
      "entity_id": "eu_002",
      "name": "Tech Imports LLC",
      "match_score": 0.80,
      "list_source": "EU",
      "reason": ""
    }
  ],
  "recommendation": "BLOCK",
  "explanation": "Amount exceeds $10,000 threshold; High-risk jurisdiction: AE; Watchlist match: Tech Imports LLC (EU, score=0.80)",
  "screened_at": "2026-08-21T10:30:00.123Z"
}
```

### Get Screening Result
```http
GET /screening/transactions/{transaction_id}
```

**Response (200 OK):**
```json
{
  "transaction_id": "tx_987654321",
  "message": "Screening result storage coming in Phase 5",
  "status": "pending"
}
```

---

## Fraud Detection

### Check Transaction for Fraud
```http
POST /fraud/check
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| transaction_id | string | Yes | Unique transaction identifier |
| user_id | string | Yes | User identifier |
| amount | float | Yes | Transaction amount (>0) |
| country | string | No | ISO country code (default: "US") |

**Response (200 OK):**
```json
{
  "transaction_id": "tx_test",
  "fraud_probability": 0.85,
  "behavioral_z_score": 3.2,
  "velocity_score": 0.0,
  "geo_anomaly": false,
  "time_anomaly": false,
  "ml_score": 0.82,
  "combined_score": 0.78,
  "recommendation": "BLOCK",
  "reason": "Amount anomaly (z=3.2); ML fraud probability=0.82",
  "scored_at": "2026-08-21T10:30:00Z"
}
```

### List Fraud Alerts
```http
GET /fraud/alerts
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | int | No | Max alerts (default: 20, max: 100) |
| status | string | No | Filter by status |

**Response (200 OK):**
```json
[
  {
    "alert_id": "alt_1",
    "transaction_id": "tx_001",
    "alert_type": "ml_fraud",
    "severity": "HIGH",
    "status": "OPEN",
    "risk_score": 0.78,
    "created_at": "2026-08-21T10:30:00Z"
  }
]
```

### Triage Fraud Alert
```http
POST /fraud/alerts/{alert_id}/triage
```

**Response (200 OK):**
```json
{
  "alert_id": "alt_1",
  "transaction_id": "tx_001",
  "confidence": 0.85,
  "recommendation": "ESCALATE",
  "risk_dossier": "Alert alt_1 for txn tx_001 (severity=HIGH, amount=$50,000). Amount z-score: 3.2 (high anomaly); High-value transaction: $50,000.",
  "evidence": ["Amount z-score: 3.2 (high anomaly)", "High-value transaction: $50,000"],
  "generated_at": "2026-08-21T10:30:05Z"
}
```

---

## Merchant Approval

### Onboard Merchant
```http
POST /merchant/onboard
Content-Type: application/json
```

**Request Body:**
```json
{
  "business_name": "Acme Corporation",
  "registration_number": "U12345MH2020PTC123456",
  "country": "IN",
  "industry": "E-commerce",
  "website": "https://acme.example.com",
  "contact_email": "contact@acme.example.com",
  "documents": [
    {"type": "INCORPORATION", "file_url": "https://example.com/doc1.pdf"}
  ]
}
```

**Response (200 OK):**
```json
{
  "merchant_id": "merch_0",
  "status": "APPROVED",
  "risk_score": 0.25,
  "kyb_status": "VERIFIED",
  "kyc_status": "NOT_STARTED",
  "ai_summary": "Composite risk: 0.25; kyb_completeness: 0.10",
  "created_at": "2026-08-21T10:30:00Z"
}
```

### Get Merchant Status
```http
GET /merchant/status/{merchant_id}
```

**Response (200 OK):**
```json
{
  "merchant_id": "merch_0",
  "status": "APPROVED",
  "message": "Merchant status tracking coming in Phase 5"
}
```

---

## Error Responses

All endpoints return standard HTTP status codes:
- `200 OK` — Success
- `400 Bad Request` — Invalid input
- `401 Unauthorized` — Invalid/missing token
- `404 Not Found` — Resource not found
- `429 Too Many Requests` — Rate limit exceeded
- `500 Internal Server Error` — Server error

**Error Response Format:**
```json
{
  "detail": "Error message here"
}
```
