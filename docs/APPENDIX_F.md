# APPENDIX F: SAMPLE SCREENING REPORTS

## Report 1: Normal Transaction (APPROVED)
```
Transaction ID: tx_normal_001
Amount: $500.00 USD
Sender: John Smith (US)
Receiver: Jane Doe (GB)

Screening Results:
  Risk Score: 0.00
  Flags: None
  Watchlist Matches: None
  Recommendation: APPROVE
  Explanation: No rules or watchlist matches triggered

Fraud Analysis:
  Fraud Probability: 0.12
  Z-Score: 0.0
  Velocity Score: 0.0
  Recommendation: APPROVE
```

## Report 2: High-Value Transaction (REVIEW)
```
Transaction ID: tx_high_value_002
Amount: $50,000.00 USD
Sender: John Smith (US)
Receiver: Jane Doe (GB)

Screening Results:
  Risk Score: 0.30
  Flags: ["amount_threshold"]
  Watchlist Matches: None
  Recommendation: REVIEW
  Explanation: Amount $50,000 exceeds threshold $10,000

Fraud Analysis:
  Fraud Probability: 0.45
  Z-Score: 2.8
  Velocity Score: 0.0
  Recommendation: VERIFY
```

## Report 3: Sanctioned Jurisdiction (BLOCKED)
```
Transaction ID: tx_sanctioned_003
Amount: $5,000.00 USD
Sender: John Smith (US)
Receiver: Tech Imports LLC (BY)

Screening Results:
  Risk Score: 0.80
  Flags: ["high_risk_jurisdiction"]
  Watchlist Matches:
    - Tech Imports LLC (EU list, score=0.80)
  Recommendation: BLOCK
  Explanation: High-risk jurisdiction: BY; Watchlist match: Tech Imports LLC

Fraud Analysis:
  Fraud Probability: 0.65
  Z-Score: 1.5
  Recommendation: BLOCK
```

## Report 4: Structuring Pattern (BLOCKED)
```
Transaction ID: tx_struct_004
Amount: $8,500.00 USD
Sender: Suspicious User (US)
Receiver: Receiver (GB)

Screening Results:
  Risk Score: 0.75
  Flags: ["structuring", "velocity"]
  Watchlist Matches: None
  Recommendation: BLOCK
  Explanation: 4 transactions below $9,000 in 24h, total $34,000

Fraud Analysis:
  Fraud Probability: 0.72
  Velocity Score: 0.7
  Recommendation: BLOCK
```

## Report 5: Round-Trip Transaction (BLOCKED)
```
Transaction ID: tx_roundtrip_005
Amount: $5,000.00 USD
Sender: Alice Brown (US)
Receiver: Alice Brown (US)

Screening Results:
  Risk Score: 0.90
  Flags: ["round_trip"]
  Watchlist Matches: None
  Recommendation: BLOCK
  Explanation: Same entity as sender and receiver: usr_123

Fraud Analysis:
  Fraud Probability: 0.55
  Recommendation: BLOCK
```
