# APPENDIX H: MERCHANT ONBOARDING WORKFLOW SCREENSHOTS

## Figure H.1: Onboarding Form
```
┌─────────────────────────────────────────────────────────────────┐
│  Merchant Onboarding Application                                │
├─────────────────────────────────────────────────────────────────┤
│  Business Name:    [Acme Corporation                      ]    │
│  Registration No:  [U12345MH2020PTC123456                ]    │
│  Country:          [IN        ▼]         Industry: [E-commerce ▼]
│  Website:          [https://acme.example.com             ]    │
│  Contact Email:    [contact@acme.example.com             ]    │
│                                                                 │
│  Upload Documents:                                              │
│  📎 Incorporation Certificate.pdf  [Remove]                   │
│  📎 Business License.pdf           [Remove]                   │
│  📎 + Add Document                                                │
│                                                                 │
│  [Submit Application]                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Figure H.2: KYB Verification Progress
```
┌─────────────────────────────────────────────────────────────────┐
│  KYB Verification Progress                                      │
├─────────────────────────────────────────────────────────────────┤
│  Step 1: Document Upload        ✅ Completed                   │
│  Step 2: OCR Extraction         ✅ Completed (95% confidence)  │
│  Step 3: Entity Resolution      ✅ Completed                   │
│  Step 4: Watchlist Screening    ✅ Completed (No matches)      │
│  Step 5: Risk Scoring           ✅ Completed (Score: 0.25)     │
│  Step 6: Final Decision         ✅ APPROVED                    │
│                                                                 │
│  Processing Time: 3.2 seconds                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Figure H.3: Risk Score Breakdown
```
┌─────────────────────────────────────────────────────────────────┐
│  Merchant Risk Assessment                                       │
├─────────────────────────────────────────────────────────────────┤
│  Composite Score: 0.25 (LOW RISK)                               │
│                                                                 │
│  Component Breakdown:                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ KYB Completeness     ████████░░  0.20 (30% weight)     │   │
│  │ Geographic Risk      ███░░░░░░░  0.10 (20% weight)     │   │
│  │ Industry Risk        █░░░░░░░░░  0.10 (15% weight)     │   │
│  │ Web Reputation       ██░░░░░░░░  0.20 (15% weight)     │   │
│  │ Sanctions Screening  ░░░░░░░░░░  0.00 (20% weight)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Recommendation: APPROVE                                        │
│  Explanation: All risk components below threshold.              │
└─────────────────────────────────────────────────────────────────┘
```

## Figure H.4: Rejected Merchant Example
```
┌─────────────────────────────────────────────────────────────────┐
│  Merchant Risk Assessment — REJECTED                            │
├─────────────────────────────────────────────────────────────────┤
│  Business: Suspicious Ltd                                       │
│  Country: IR (Iran)                                             │
│  Industry: Crypto                                               │
│                                                                 │
│  Composite Score: 0.85 (HIGH RISK)                              │
│                                                                 │
│  Component Breakdown:                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ KYB Completeness     ██████████  0.80 (30% weight)     │   │
│  │ Geographic Risk      ██████████  0.80 (20% weight)     │   │
│  │ Industry Risk        ████████░░  0.70 (15% weight)     │   │
│  │ Web Reputation       ██████░░░░  0.50 (15% weight)     │   │
│  │ Sanctions Screening  ██████████  0.90 (20% weight)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Risk Indicators:                                               │
│  • High-risk jurisdiction: IR                                   │
│  • High-risk industry: Crypto                                   │
│  • Sanctions match: Possible affiliation                        │
│                                                                 │
│  Recommendation: REJECT                                         │
└─────────────────────────────────────────────────────────────────┘
```
