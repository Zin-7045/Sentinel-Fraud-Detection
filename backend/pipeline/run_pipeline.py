import json, time, sys, os, numpy as np
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.pipeline.data_ingestion import TransactionProducer
from backend.models.ensemble import FraudEnsemble
from backend.storage.postgres_client import PostgresClient
from backend.storage.redis_cache import RedisCache
from backend.storage.mongodb_logger import MongoLogger

pg = PostgresClient()
redis_cache = RedisCache()
mongo = MongoLogger()
ensemble = FraudEnsemble()
producer = TransactionProducer()

pg.init_schema()
print("[OK] PostgreSQL schema initialized")
print("[..] Generating 500 transactions and storing via ML pipeline...\n")

for i in range(500):
    txn = producer.generate()
    ts = datetime.fromisoformat(txn["timestamp"])

    features = np.array([
        float(txn["amount"]),           # transaction_amount
        0.0,                            # velocity_1h
        0.5,                            # merchant_risk_score
        0.0,                            # geo_anomaly_score
        0.8,                            # device_fingerprint_match
        1.0,                            # time_since_last_txn
        0.0,                            # amount_vs_avg_30d
        0.0,                            # channel_frequency_score
        float(ts.hour),                 # hour_of_day
        float(ts.weekday()),            # day_of_week
        1.0 if txn["amount"] > 500 else 0.0,  # is_high_amount
        1.0 if txn["region"] in ["APAC", "LATAM", "ME-AF"] else 0.0,  # is_cross_border
    ], dtype=np.float32)

    result = ensemble.predict(features)

    pg.insert("transactions", {
        "transaction_id": txn["transaction_id"],
        "timestamp": txn["timestamp"],
        "user_id": txn["user_id"],
        "merchant": txn["merchant"],
        "amount": float(txn["amount"]),
        "channel": txn["channel"],
        "region": txn["region"],
        "risk_score": int(txn["risk_score"]),
        "status": txn["status"],
        "is_fraud": bool(txn["is_fraud"]),
        "fraud_type": txn.get("fraud_type"),
    })

    pg.insert("predictions", {
        "transaction_id": txn["transaction_id"],
        "fraud_probability": float(result.fraud_probability),
        "risk_score": int(result.risk_score),
        "is_fraud": bool(result.is_fraud),
        "model_scores": str(result.model_scores),
        "factors": ",".join(result.contributing_factors),
        "timestamp": txn["timestamp"],
    })

    if result.is_fraud and result.risk_score > 80:
        mongo.log_alert(
            txn_id=txn["transaction_id"],
            fraud_type=txn.get("fraud_type") or "Unknown",
            risk_score=int(result.risk_score),
            merchant=txn["merchant"],
            user_id=txn["user_id"],
            region=txn["region"],
            score=float(result.fraud_probability),
        )

    redis_cache.incr("etl:total_count")
    if txn["is_fraud"]:
        redis_cache.incr("etl:fraud_count")
    redis_cache.set("etl:avg_risk", float(result.risk_score), ttl=3600)

    if (i + 1) % 50 == 0:
        print(f"  Processed {i+1}/500 transactions...")

print(f"\n[OK] Done! Processed {500} transactions")
print("[OK] PostgreSQL has transactions + predictions")
print("[OK] Redis has live counters")
print("[OK] MongoDB has fraud alerts")
print("\nNow open http://localhost:3001 -- dashboard will show real data from the API")
