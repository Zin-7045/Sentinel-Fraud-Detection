# Sentinel — Big Data Analytics Fraud Detection Platform

A production-grade, end-to-end **Big Data Analytics pipeline** for **real-time fraud detection** in financial transactions. Built with Apache Kafka, Spark Streaming, ensemble ML models (Isolation Forest + XGBoost + LSTM), and a live React dashboard.

**Course:** CSDS4473 Big Data Analytics — University of Central Punjab

---

## Overview

Sentinel ingests synthetic financial transactions (~6–10% fraud rate) via Kafka, processes them through Spark Structured Streaming, extracts 12 engineered features, runs an ensemble of 3 ML models for fraud classification, and surfaces everything through a FastAPI backend and real-time React dashboard.

### Key Results

| Metric | Value |
|--------|-------|
| **Ensemble AUC-ROC** | ~95% |
| **XGBoost AUC-ROC** | ~94% |
| **Isolation Forest AUC-ROC** | ~85% |
| **Fraud Rate** | 6–10% |
| **Top Feature** | `transaction_amount` (23.1% importance) |
| **Throughput** | ~1.25 txn/s (800ms interval) |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA INGESTION LAYER                               │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────────┐      │
│  │  Transaction     │  │   Kafka      │  │  REST API                  │      │
│  │  Generator (PRNG)│──▶  Topics      │◀─│  /api/v1/predict           │      │
│  │  seed=42         │  │  txn.raw     │  │  /api/v1/predict/batch     │      │
│  └─────────────────┘  │  fraud.alerts │  └────────────────────────────┘      │
│                       └───────┬───────┘                                      │
├───────────────────────────────┼─────────────────────────────────────────────┤
│                               │            PROCESSING LAYER                  │
│  ┌────────────────────────────▼─────────────────────────────────────────┐   │
│  │  Spark Structured Streaming (30s windows, 15s slides)                │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │   │
│  │  │  Enrichment      │  │  Windowed Aggr.  │  │  Feature         │   │   │
│  │  │  (amount_cat,    │  │  (count, sum,    │  │  Extraction (12) │   │   │
│  │  │   risk_level,    │  │   avg by window) │  │  → model.inputs  │   │   │
│  │  │   cross_border)  │  │                  │  │                  │   │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                             │
├───────────────────────────────┼─────────────────────────────────────────────┤
│                               │           ML INFERENCE LAYER                │
│  ┌────────────────────────────▼─────────────────────────────────────────┐   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │   │
│  │  │  Isolation Forest │  │  XGBoost         │  │  LSTM            │   │   │
│  │  │  (unsupervised)   │  │  (supervised)    │  │  (sequence)      │   │   │
│  │  │  200 estimators  │  │  300 estimators  │  │  128→64→1        │   │   │
│  │  │  contamination=5%│  │  max_depth=8     │  │  seq_len=10      │   │   │
│  │  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │   │
│  │           └──────────┬──────────┘                     │             │   │
│  │                      └────────────────┬───────────────┘             │   │
│  │                                       ▼                             │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │  Ensemble (weighted voting): XGB 45% + LSTM 30% + IF 25%     │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                             │
├───────────────────────────────┼─────────────────────────────────────────────┤
│                               │              STORAGE LAYER                   │
│  ┌────────────────────────────▼─────────────────────────────────────────┐   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │   │
│  │  │  PostgreSQL   │  │   Redis      │  │   MongoDB    │                │   │
│  │  │  transactions │  │  live cache  │  │  fraud alerts│                │   │
│  │  │  predictions  │  │  metrics     │  │  audit log   │                │   │
│  │  │  alerts       │  │  counters    │  │  TTL: 7 days │                │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Dataset

Synthetic financial transaction dataset generated with a deterministic PRNG (seed=42).

| Field | Description |
|-------|-------------|
| `transaction_id` | UUID v4 |
| `timestamp` | ISO 8601 datetime (spans 24h) |
| `user_id` | UUID (pool of 500 users) |
| `merchant_id` | UUID (pool of 200 merchants) |
| `transaction_amount` | Float (non-negative, log-normal) |
| `currency` | USD, EUR, GBP, PKR, AED, SAR |
| `transaction_type` | TRANSFER, PAYMENT, WITHDRAWAL, DEPOSIT |
| `channel` | ATM, POS, WEB, MOBILE_APP |
| `region` | SAARC, ME-AF, LATAM, ASEAN, EAST-EU, WEST-EU, NA |
| `is_fraud` | Boolean (6–10% true) |
| `fraud_type` | CHARGEBACK, ACCOUNT_TAKEOVER, PHISHING, IDENTITY_THEFT, CARD_NOT_PRESENT, SYNTHETIC_ID |
| `device_fingerprint` | UUID (pool of 1000 devices) |
| `ip_address` | Random IPv4 |
| `risk_score` | Float (0–1, correlated with fraud) |
| `merchant_category` | GROCERY, ELECTRONICS, TRAVEL, etc. |
| `is_cross_border` | Boolean |

The dataset is **470MB (6.36M rows)** and excluded from version control. Generate it via:

```python
from backend.pipeline.data_ingestion import TransactionProducer
tp = TransactionProducer(num_transactions=10000)
df = tp.generate()
df.to_csv("dataset.csv", index=False)
```

---

## Feature Engineering

12 features extracted per transaction for ML inference:

| Feature | Description | Type |
|---------|-------------|------|
| `velocity_1h` | Transaction count in last hour per user | Temporal |
| `merchant_risk_score` | Historical fraud rate per merchant | Behavioral |
| `geo_anomaly_score` | Region change frequency per user | Behavioral |
| `device_fingerprint_match` | Device reuse across users count | Identity |
| `time_since_last_txn` | Minutes since user's last transaction | Temporal |
| `amount_vs_avg_30d` | Amount / user's 30-day average | Statistical |
| `channel_frequency_score` | Channel diversity per user | Behavioral |
| `hour_of_day` | Extracted from timestamp | Cyclical |
| `day_of_week` | Extracted from timestamp | Cyclical |
| `is_high_amount` | Amount > 95th percentile | Threshold |
| `is_cross_border` | From transaction data | Binary |
| `risk_score` | Pre-computed risk indicator | Score |

---

## ML Models

### Isolation Forest (Unsupervised)
- **Algorithm**: scikit-learn `IsolationForest`
- **Parameters**: 200 estimators, contamination=0.05
- **AUC-ROC**: ~85%
- **Use case**: Anomaly detection without labeled data

### XGBoost (Supervised)
- **Algorithm**: `XGBClassifier` with scale_pos_weight=5.0
- **Parameters**: 300 estimators, max_depth=8, early stopping rounds=20
- **AUC-ROC**: ~94%
- **Use case**: Binary classification with imbalanced classes

### LSTM (Deep Learning)
- **Architecture**: LSTM(128) → Dropout(0.3) → LSTM(64) → Dropout(0.3) → Dense(32) → Dense(1, sigmoid)
- **Sequence length**: 10 transactions
- **Use case**: Sequential pattern recognition

### Ensemble (Weighted Voting)
- **Weights**: XGBoost 45% + LSTM 30% + Isolation Forest 25%
- **Fallback**: Heuristic rules if models unavailable
- **Final AUC-ROC**: ~95%

**Feature Importance (XGBoost):**
| Feature | Importance |
|---------|-----------|
| `transaction_amount` | 23.1% |
| `velocity_1h` | 18.7% |
| `merchant_risk_score` | 16.2% |
| `geo_anomaly_score` | 14.1% |
| `device_fingerprint_match` | 9.8% |
| Others | 18.1% |

---

## Visualizations

### Notebook-Generated (Matplotlib/Seaborn)

The `notebooks/04_fraud_dashboard_visualizations.ipynb` generates:

| Chart | Insight |
|-------|---------|
| **KPI Dashboard** | Total transactions, fraud count, fraud rate, avg risk score |
| **24h Time-Series** | Transaction volume + fraud count by hour (dual-axis) |
| **Fraud Rate by Region** | ME-AF and LATAM highest (12–15%) |
| **Fraud Rate by Channel** | ATM, POS most vulnerable |
| **Fraud Heatmap** | Region × Channel fraud rate matrix |
| **ROC Curves** | Model comparison (Ensemble ~95% AUC) |
| **Confusion Matrix** | XGBoost prediction accuracy |
| **Feature Importance** | Top predictive features ranked |
| **PCA Anomaly Clusters** | Fraud vs. clean transaction separation |
| **Fraud Type Distribution** | Pie chart of fraud categories |

### Live Dashboard (React + Recharts)

The frontend dashboard (`FraudDetectionDashboard.jsx`) renders real-time:

- **6 animated KPI cards** with sparklines
- **24h area chart** — transaction stream with fraud overlay
- **Radar chart** — 6 model performance metrics
- **Heatmap grid** — Region × Channel fraud rates
- **Network graph** — User-merchant entity relationships (Canvas)
- **Scatter plot** — Isolation Forest anomaly cluster visualization
- **Throughput & latency charts**
- **Model performance table** — 5 models compared
- **Feature importance bars** — XGBoost feature ranking
- **Pipeline architecture view** — Live status indicators
- **Alert banner** — Real-time push notifications

---

## Tech Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Streaming** | Apache Kafka 7.6.0 | Message queue & event bus |
| **Stream Processing** | Apache Spark 3.5.1 (PySpark) | Distributed stream processing |
| **Anomaly Detection** | scikit-learn (Isolation Forest) | Unsupervised fraud detection |
| **Classification** | XGBoost 2.0.3 | Supervised fraud classification |
| **Deep Learning** | TensorFlow/Keras (LSTM) | Sequence modeling |
| **API** | FastAPI + Uvicorn | REST backend |
| **Frontend** | React 18 + Vite 5 + Recharts | Live dashboard |
| **Databases** | PostgreSQL 16 (txns), Redis 7 (cache), MongoDB 7 (alerts) | Multi-model storage |
| **Orchestration** | Docker Compose | Infrastructure management |
| **Monitoring** | Prometheus metrics | System observability |

---

## Project Structure

```
D:\BDA
├── backend/                          # Python Big Data pipeline
│   ├── api/
│   │   ├── main.py                   # FastAPI entry point + CORS
│   │   └── routes.py                 # 7 REST endpoints
│   ├── models/
│   │   ├── isolation_forest.py       # Unsupervised anomaly detector
│   │   ├── xgboost_model.py          # Gradient boosted classifier
│   │   ├── lstm_detector.py          # LSTM sequence model
│   │   ├── ensemble.py               # Weighted voting ensemble
│   │   └── model_registry.py         # Versioned model management
│   ├── pipeline/
│   │   ├── data_ingestion.py         # Synthetic transaction generator (PRNG)
│   │   ├── stream_processor.py       # Spark Structured Streaming enrichment
│   │   ├── feature_engineering.py    # 12 feature extractors
│   │   ├── etl_pipeline.py           # Batch ETL → Postgres/Redis/Mongo
│   │   ├── kafka_pipeline.py         # Kafka producer + consumer helpers
│   │   └── kafka_producer_runner.py  # Standalone transaction streamer
│   ├── streaming/
│   │   ├── kafka_producer.py         # Kafka message producer
│   │   ├── kafka_consumer.py         # Kafka consumer + ML inference
│   │   └── spark_streaming.py        # PySpark Structured Streaming job
│   ├── storage/
│   │   ├── postgres_client.py        # PostgreSQL CRUD (transactions, predictions, alerts)
│   │   ├── redis_cache.py            # Redis in-memory cache for live metrics
│   │   └── mongodb_logger.py         # MongoDB audit log (7-day TTL)
│   ├── monitoring/
│   │   ├── metrics_collector.py      # Prometheus metrics (CPU, memory, latency)
│   │   └── alert_manager.py          # Alert routing (webhook, email)
│   ├── config.py                     # Central configuration
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                         # React dashboard
│   └── src/
│       ├── components/
│       │   └── FraudDetectionDashboard.jsx  # 991-line dashboard
│       ├── App.jsx
│       └── main.jsx
│
├── notebooks/                        # Jupyter data science workflow
│   ├── 01_exploratory_data_analysis.py      # EDA: distributions, correlations, fraud patterns
│   ├── 02_feature_engineering.py            # Feature extraction & selection
│   ├── 03_model_training.py                 # Model training + evaluation
│   ├── 04_fraud_dashboard_visualizations.ipynb  # All visualizations
│   └── bda_fraud_detection_colab.ipynb      # Full Colab pipeline (1350 lines)
│
├── streaming/                        # Spark jobs
│   ├── spark_job.py                  # Structured Streaming with windowing
│   ├── minimal_spark_job.py          # Spark batch demo
│   ├── spark_batch_analysis.py       # CSV batch analysis
│   └── submit_spark_job.sh           # Job submission script
│
├── docker-compose.yml                # Full infrastructure (Kafka, Spark, DBs)
├── Dockerfile                        # API container
├── run.bat                           # Windows launcher
├── project_report.md                 # Academic project report
├── dataset_description.md            # Dataset schema documentation
└── Project_Run_Flow.txt              # Step-by-step run guide
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 1. Infrastructure
```bash
docker-compose up -d
```
Starts: Kafka + Zookeeper, PostgreSQL, Redis, MongoDB, Spark (master + worker).

### 2. Backend API
```bash
cd backend
pip install -r requirements.txt
python -m api.main
```
FastAPI at `http://localhost:8000` — docs at `http://localhost:8000/docs`

### 3. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Dashboard at `http://localhost:3001`

### 4. Stream Transactions
```bash
# Generate & publish synthetic transactions to Kafka
python backend/pipeline/kafka_producer_runner.py

# Or generate inline
python -c "
from backend.streaming.kafka_producer import FraudKafkaProducer
FraudKafkaProducer().stream_continuous(interval_ms=800)
"
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/api/v1/transactions` | List transactions (paginated, filterable) |
| POST | `/api/v1/predict` | Single transaction fraud prediction |
| POST | `/api/v1/predict/batch` | Batch predictions |
| GET | `/api/v1/metrics` | Live dashboard metrics |
| GET | `/api/v1/alerts` | Recent fraud alerts |
| GET | `/api/v1/pipeline/status` | All pipeline component health |

---

## Running the Notebooks

```bash
# Convert .py to .ipynb and run
jupyter nbconvert --to notebook notebooks/01_exploratory_data_analysis.py
jupyter notebook
```

Recommended order:
1. `01_exploratory_data_analysis` — Understand data distributions & fraud patterns
2. `02_feature_engineering` — Feature extraction & correlation analysis
3. `03_model_training` — Train & evaluate all 3 models
4. `04_fraud_dashboard_visualizations` — Generate all charts
5. `bda_fraud_detection_colab.ipynb` — Full end-to-end (works in Google Colab)

---

## Key Insights

1. **ME-AF and LATAM regions** show the highest fraud rates (12–15%), suggesting targeted fraud rings
2. **ATM and POS channels** are significantly more vulnerable than WEB/MOBILE
3. **Transaction amount** is the single most predictive feature (23.1% importance)
4. **Velocity (txn frequency)** is the second strongest signal (18.7%) — rapid successive transactions strongly indicate fraud
5. **Fraud transactions form distinct clusters** in PCA space, confirming separability
6. **Ensemble model (~95% AUC)** outperforms any individual model by 1–10%
7. The **XGBoost + Isolation Forest combination** provides both supervised accuracy and unsupervised anomaly coverage

---

## BDA Techniques

| Technique | Implementation |
|-----------|---------------|
| Stream Processing | Kafka + Spark Structured Streaming (30s windows, 15s slides) |
| Feature Engineering | 12 temporal, behavioral & statistical features |
| Anomaly Detection | Isolation Forest (200 estimators, 5% contamination) |
| Supervised Learning | XGBoost (scale_pos_weight=5.0, early stopping) |
| Sequence Modeling | LSTM (128→64→1, sequence length 10) |
| Ensemble Learning | Weighted voting (XGB 45% + LSTM 30% + IF 25%) |
| Distributed Computing | PySpark for parallel stream processing |
| In-Memory Caching | Redis for sub-millisecond metrics retrieval |
| Time-Series Storage | PostgreSQL (OLTP) + MongoDB (document/audit) |
| Real-Time Alerts | Kafka fraud.alerts topic + webhook/email routing |
| Model Registry | Versioned .pkl persistence with promote/archive lifecycle |
| Containerization | Docker Compose for 7+ service orchestration |

---

## Acknowledgments

- **PaySim** dataset for synthetic mobile money transactions (inspiration)
- Apache Kafka, Spark, scikit-learn, XGBoost, TensorFlow open-source communities
- Course Big Data Analytics 

**Team:** Muhammad Nabeel Arshad, Muhammad Zain, Abdur Rehman (Zin-7045)
