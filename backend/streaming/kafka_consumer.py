import json
from kafka import KafkaConsumer as KConsumer
from typing import Callable, Optional

from backend.config import KAFKA_BROKER, KAFKA_RAW_TOPIC, KAFKA_ALERT_TOPIC
from backend.models.ensemble import FraudEnsemble
from backend.pipeline.feature_engineering import FeatureEngineer
from backend.storage.postgres_client import PostgresClient
from backend.storage.mongodb_logger import MongoLogger


class FraudKafkaConsumer:
    def __init__(self, bootstrap_servers: str = KAFKA_BROKER,
                 group_id: str = "fraud-detection-group"):
        self.consumer = KConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
        )
        self.ensemble = FraudEnsemble()
        self.engineer = FeatureEngineer()
        self.pg = PostgresClient()
        self.mongo = MongoLogger()
        self.running = False

    def process_transaction(self, txn: dict):
        features = self.engineer.extract_features(txn)
        prediction = self.ensemble.predict(features)
        txn["ensemble_score"] = prediction.fraud_probability
        txn["ensemble_risk"] = prediction.risk_score
        txn["contributing_factors"] = prediction.contributing_factors
        self.pg.insert("predictions", {
            "transaction_id": txn["transaction_id"],
            "fraud_probability": prediction.fraud_probability,
            "risk_score": prediction.risk_score,
            "is_fraud": prediction.is_fraud,
            "model_scores": str(prediction.model_scores),
            "factors": ",".join(prediction.contributing_factors),
            "timestamp": txn["timestamp"],
        })
        if prediction.is_fraud and prediction.risk_score > 80:
            self.mongo.insert("fraud_alerts", {
                "transaction_id": txn["transaction_id"],
                "fraud_type": txn.get("fraud_type"),
                "risk_score": prediction.risk_score,
                "merchant": txn["merchant"],
                "user_id": txn["user_id"],
                "region": txn["region"],
                "score": prediction.fraud_probability,
                "timestamp": txn["timestamp"],
            })

    def consume(self, topics: list = None):
        topics = topics or [KAFKA_RAW_TOPIC]
        self.consumer.subscribe(topics)
        self.running = True
        try:
            for msg in self.consumer:
                if not self.running:
                    break
                self.process_transaction(msg.value)
        finally:
            self.consumer.close()

    def stop(self):
        self.running = False


class AlertConsumer:
    def __init__(self, bootstrap_servers: str = KAFKA_BROKER):
        self.consumer = KConsumer(
            KAFKA_ALERT_TOPIC,
            bootstrap_servers=bootstrap_servers,
            group_id="alert-consumer-group",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        self.callbacks: list[Callable] = []

    def on_alert(self, callback: Callable):
        self.callbacks.append(callback)

    def consume_alerts(self):
        for msg in self.consumer:
            for cb in self.callbacks:
                cb(msg.value)
