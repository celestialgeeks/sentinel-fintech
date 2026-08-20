# APPENDIX C: DATABASE SCHEMA DDL

## PostgreSQL Schema (SQLAlchemy 2.0)

```sql
-- Transactions table
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount FLOAT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    sender_id VARCHAR(128),
    sender_name VARCHAR(256),
    sender_country VARCHAR(2),
    receiver_id VARCHAR(128),
    receiver_name VARCHAR(256),
    receiver_country VARCHAR(2),
    ip_address VARCHAR(45),
    device_fingerprint VARCHAR(256),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    risk_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_txns_sender_country ON transactions(sender_country);
CREATE INDEX ix_txns_receiver_country ON transactions(receiver_country);
CREATE INDEX ix_txns_status_risk ON transactions(status, risk_score);
CREATE INDEX ix_txns_created_at ON transactions(created_at);

-- Screening Results table
CREATE TABLE screening_results (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    risk_score FLOAT,
    flags JSONB,
    matched_entities JSONB,
    recommendation VARCHAR(20) NOT NULL,
    confidence FLOAT,
    explanation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_screening_txn_id ON screening_results(transaction_id);
CREATE INDEX ix_screening_recommendation ON screening_results(recommendation);
CREATE INDEX ix_screening_created_at ON screening_results(created_at);

-- Fraud Alerts table
CREATE TABLE fraud_alerts (
    id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT REFERENCES transactions(id) ON DELETE SET NULL,
    alert_type VARCHAR(128) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    risk_score FLOAT,
    triage_recommendation VARCHAR(256),
    agent_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX ix_alerts_severity_status ON fraud_alerts(severity, status);
CREATE INDEX ix_alerts_created_at ON fraud_alerts(created_at);
CREATE INDEX ix_alerts_transaction_id ON fraud_alerts(transaction_id);

-- Merchants table
CREATE TABLE merchants (
    id BIGSERIAL PRIMARY KEY,
    business_name VARCHAR(256) NOT NULL,
    registration_number VARCHAR(64),
    country VARCHAR(2),
    industry VARCHAR(128),
    risk_score FLOAT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    kyb_status VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED',
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_merchants_reg_number ON merchants(registration_number);
CREATE INDEX ix_merchants_status ON merchants(status);
CREATE INDEX ix_merchants_country ON merchants(country);
CREATE INDEX ix_merchants_created_at ON merchants(created_at);

-- User Profiles table
CREATE TABLE user_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(128) UNIQUE NOT NULL,
    name VARCHAR(256),
    country VARCHAR(2),
    device_fingerprint VARCHAR(256),
    typical_amount_min FLOAT,
    typical_amount_max FLOAT,
    typical_countries JSONB,
    profile_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_profiles_device_fp ON user_profiles(device_fingerprint);

-- Entity Graph table
CREATE TABLE entity_graph (
    id BIGSERIAL PRIMARY KEY,
    source_entity_id VARCHAR(128) NOT NULL,
    target_entity_id VARCHAR(128) NOT NULL,
    relationship_type VARCHAR(128) NOT NULL,
    weight FLOAT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_entity_graph_unique ON entity_graph(source_entity_id, target_entity_id, relationship_type);
CREATE INDEX ix_entity_graph_source ON entity_graph(source_entity_id, relationship_type);
CREATE INDEX ix_entity_graph_target ON entity_graph(target_entity_id, relationship_type);

-- Audit Log table
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    user VARCHAR(128),
    result VARCHAR(32),
    details JSONB,
    ip_address VARCHAR(45)
);

CREATE INDEX ix_audit_timestamp ON audit_log(timestamp);
CREATE INDEX ix_audit_entity ON audit_log(entity_type, entity_id);
```

## Milvus Collection Schema

```python
# Collection: entities
fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema(name="entity_type", dtype=DataType.VARCHAR, max_length=32),
    FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
    FieldSchema(name="metadata", dtype=DataType.JSON),
    FieldSchema(name="score", dtype=DataType.FLOAT),
]

index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "IP",
    "params": {"nlist": 128}
}
```

## Neo4j Schema

```cypher
-- Node labels
:CARD (Company)
:INDIVIDUAL (Person)
:ACCOUNT (BankAccount)
:DEVICE (Device)
:IP_ADDRESS (IPAddress)

-- Relationships
(:INDIVIDUAL)-[:OWNS]->(:ACCOUNT)
(:ACCOUNT)-[:SENT_TO]->(:ACCOUNT)
(:ACCOUNT)-[:SHARED_DEVICE]->(:DEVICE)
(:ACCOUNT)-[:SAME_IP]->(:ACCOUNT)
(:INDIVIDUAL)-[:SAME_PHONE]->(:INDIVIDUAL)
```
