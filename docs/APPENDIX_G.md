# APPENDIX G: FRAUD ALERT DASHBOARD SCREENSHOTS

## Figure G.1: Fraud Alert List View
```
┌─────────────────────────────────────────────────────────────────┐
│  Sentinel Fraud Dashboard                                       │
├─────────────────────────────────────────────────────────────────┤
│  Alert ID    │ Transaction  │ Severity │ Status    │ Score     │
├──────────────┼──────────────┼──────────┼───────────┼───────────┤
│ alt_001      │ tx_001       │ HIGH     │ OPEN      │ 0.78      │
│ alt_002      │ tx_002       │ MEDIUM   │ OPEN      │ 0.52      │
│ alt_003      │ tx_003       │ CRITICAL │ INVESTIGATING│ 0.91    │
│ alt_004      │ tx_004       │ LOW      │ RESOLVED   │ 0.23      │
└─────────────────────────────────────────────────────────────────┘
```

## Figure G.2: Alert Triage Report
```
┌─────────────────────────────────────────────────────────────────┐
│  Triage Report: alt_003                                        │
├─────────────────────────────────────────────────────────────────┤
│  Transaction: tx_003                                           │
│  Severity: CRITICAL                                             │
│  Confidence: 0.92                                               │
│  Recommendation: ESCALATE                                       │
│                                                                 │
│  Evidence:                                                      │
│  • Amount z-score: 4.2 (high anomaly)                          │
│  • Velocity: 8 transactions in 30 minutes                      │
│  • Connected to 3 entities in fraud graph                      │
│  • IP reputation score: 0.85 (high risk)                       │
│                                                                 │
│  Risk Dossier:                                                  │
│  Alert alt_003 for txn tx_003 (severity=CRITICAL,              │
│  amount=$45,000). Amount z-score: 4.2 (high anomaly);          │
│  Velocity anomaly detected (score=0.80); Connected to 3        │
│  entities in fraud graph; IP reputation score: 0.85 (high      │
│  risk).                                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Figure G.3: Merchant Onboarding Status
```
┌─────────────────────────────────────────────────────────────────┐
│  Merchant Onboarding: merch_001                                 │
├─────────────────────────────────────────────────────────────────┤
│  Business: Acme Corporation                                     │
│  Country: IN                                                    │
│  Industry: E-commerce                                           │
│                                                                 │
│  KYB Status: VERIFIED ✅                                        │
│  KYC Status: PENDING ⏳                                         │
│  Risk Score: 0.25 (LOW)                                         │
│  Recommendation: APPROVED ✅                                    │
│                                                                 │
│  AI Summary: Business registered in India, low-risk industry,  │
│  clean sanctions check.                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Figure G.4: Screening Results Dashboard
```
┌─────────────────────────────────────────────────────────────────┐
│  Transaction Screening Results                                  │
├─────────────────────────────────────────────────────────────────┤
│  Total Screened: 1,247                                          │
│  Approved: 1,156 (92.7%)                                        │
│  Reviewed: 68 (5.5%)                                            │
│  Blocked: 23 (1.8%)                                             │
│                                                                 │
│  Today's Activity:                                              │
│  • Screening throughput: 45 txns/min                            │
│  • Avg latency: 32ms                                            │
│  • False positive rate: 7.2%                                    │
└─────────────────────────────────────────────────────────────────┘
```
