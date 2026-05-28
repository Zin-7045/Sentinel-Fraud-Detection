# Dataset Description

## Synthetic Financial Transaction Dataset

### Overview
A synthetic dataset of financial transactions generated using a deterministic pseudo-random generator (seed=42). Designed to simulate realistic banking transaction patterns with embedded fraud cases for ML model training and evaluation.

### Data Generation
- **Generator:** `TransactionProducer` class (`backend/pipeline/data_ingestion.py`)
- **Generation method:** Linear congruential generator for reproducibility (seed=42)
- **Size:** Configurable (5000-10000+ records), generated on-the-fly
- **Fraud rate:** ~6-10% of transactions are fraudulent
- **Fraud assignment:** A transaction is flagged as fraud if `risk_score > 72` OR random probability < 6%

### Schema (16 Fields)

| # | Field | Type | Description | Example |
|---|-------|------|-------------|---------|
| 1 | `transaction_id` | String | Unique transaction identifier | `TXN-0000001` |
| 2 | `timestamp` | DateTime | Transaction timestamp (UTC) | `2025-01-15T14:30:00` |
| 3 | `amount` | Float | Transaction amount in USD ($0.50 - $50,000) | `1245.67` |
| 4 | `merchant` | String | Merchant name (8 possible) | `TechMart Pro` |
| 5 | `region` | String | Geographic region (6 possible) | `NA-EAST` |
| 6 | `channel` | String | Transaction channel (5 possible) | `WEB`, `MOBILE`, `ATM`, `POS`, `API` |
| 7 | `fraud_type` | String or null | Type of fraud if applicable (6 types) | `Card Skimming` |
| 8 | `risk_score` | Integer | Risk score 0-99 (higher = riskier) | `72` |
| 9 | `status` | String | Transaction status (5 possible) | `FLAGGED` |
| 10 | `user_id` | String | User identifier (USR-0001 to USR-9999) | `USR-1234` |
| 11 | `is_fraud` | Boolean | Ground truth fraud label | `True` |
| 12 | `latitude` | Float | Latitude coordinate | `40.7128` |
| 13 | `longitude` | Float | Longitude coordinate | `-74.0060` |
| 14 | `device_id` | String | Device fingerprint hash | `a1b2c3d4` |
| 15 | `ip_address` | String | IP address | `192.168.1.1` |
| 16 | `processing_ms` | Integer | Processing time in milliseconds | `45` |

### Fraud Types
| Type | Description |
|------|-------------|
| Card Skimming | Unauthorized card data capture |
| Account Takeover | User account compromised |
| Synthetic ID | Fake identity used for fraud |
| Money Mule | Illicit fund transfer through accounts |
| Phishing | Credential theft via deception |
| CNP Fraud | Card-not-present transaction fraud |

### Regions
`NA-EAST`, `NA-WEST`, `EU-WEST`, `APAC`, `LATAM`, `ME-AF`

### Merchants
`TechMart Pro`, `GlobalPay`, `SwiftShop`, `NexCommerce`, `PayHub`, `CryptoXchange`, `LuxuryGoods`, `BetaPay`

### Dataset Statistics (Sample: 5000 records)
| Metric | Value |
|--------|-------|
| Total transactions | 5000 |
| Fraud count | ~300-500 (6-10%) |
| Avg transaction amount | ~$25,000 |
| Min amount | $0.50 |
| Max amount | $50,000 |
| Avg risk score | ~50 |

### Usage
```python
from backend.pipeline.data_ingestion import TransactionProducer

producer = TransactionProducer(seed=42)
transaction = producer.generate()       # single transaction
transactions = [producer.generate() for _ in range(1000)]  # batch of 1000
```
