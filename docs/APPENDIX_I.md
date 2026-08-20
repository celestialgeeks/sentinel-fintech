# APPENDIX I: ETHICS APPROVAL AND DATA PRIVACY STATEMENT

## Data Privacy Compliance

### GDPR Compliance
Sentinel is designed to comply with the General Data Protection Regulation (GDPR) requirements:
1. **Data Minimization**: Only necessary personal data is collected and processed
2. **Purpose Limitation**: Data is used solely for compliance and fraud prevention
3. **Storage Limitation**: Data retention policies are enforced (30-day rolling window for behavioral profiles)
4. **Accuracy**: Data verification checks ensure accuracy of extracted information
5. **Confidentiality**: All data is encrypted at rest (AES-256) and in transit (TLS 1.3)
6. **Integrity**: Immutable audit trails ensure data integrity

### Data Protection Measures
- **Encryption**: AES-256 for data at rest, TLS 1.3 for data in transit
- **Access Control**: JWT-based authentication with role-based access
- **Audit Logging**: All data access logged with timestamp and user
- **Data Retention**: Automatic purging of behavioral data after 30 days
- **Anonymization**: PII excluded from model training data

## Ethics Statement

### Algorithmic Fairness
1. **Bias Mitigation**: The synthetic training data is balanced across demographics
2. **Explainability**: All decisions include human-readable explanations
3. **Human Oversight**: High-severity alerts require human review before action
4. **Appeal Process**: Affected parties can request review of automated decisions

### Transparency
1. **Model Documentation**: All models and their performance are documented
2. **Decision Logs**: Every screening decision is logged with features and scores
3. **Open Source**: Source code and methodology are publicly available
4. **Regulatory Alignment**: Design follows FATF, OFAC, and EU AI Act guidelines

### Responsible AI
1. **No Discrimination**: Decisions based on transaction patterns, not protected attributes
2. **Proportionality**: Risk scores proportional to actual threat level
3. **Accountability**: Clear ownership of automated decisions
4. **Safety**: Fail-open design (blocked transactions can be reviewed and released)

## Research Ethics
This project uses entirely synthetic data generated for research purposes. No real personal or financial data was used. The synthetic dataset was generated with controlled parameters to simulate realistic fraud patterns while ensuring no real individuals are represented.
