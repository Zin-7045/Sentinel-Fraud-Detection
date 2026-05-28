import json
import time
import threading
from kafka import KafkaProducer, KafkaConsumer
from backend.config import KAFKA_BROKER, KAFKA_RAW_TOPIC, KAFKA_ALERT_TOPIC, KAFKA_PREDICTIONS_TOPIC
from backend.models.ensemble import FraudEnsemble
from backend.pipeline.feature_engineering import FeatureEngineer


class KafkaClient:
    def __init__(self, broker=KAFKA_BROKER):
        self.broker = broker
        self._producer = None
        self._ensemble = None
        self._engineer = None

    @property
    def producer(self):
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.broker,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: str(k).encode("utf-8"),
                acks="all",
                retries=3,
            )
        return self._producer

    def send(self, topic, value, key=None):
        self.producer.send(topic, value=value, key=key)
        self.producer.flush()

    def close(self):
        if self._producer:
            self._producer.close()

    def predict_and_publish(self, txn: dict) -> dict:
        if self._ensemble is None:
            self._ensemble = FraudEnsemble()
            self._ensemble.load_models()
        if self._engineer is None:
            self._engineer = FeatureEngineer()

        features = self._engineer.paysim_extract_features(txn)
        result = self._ensemble.predict(features)
        prediction = {
            "transaction_id": txn.get("transaction_id"),
            "user_id": txn.get("user_id", txn.get("nameOrig", "UNKNOWN")),
            "is_fraud": bool(result.is_fraud),
            "fraud_probability": float(result.fraud_probability),
            "risk_score": int(result.risk_score),
            "factors": list(result.contributing_factors),
            "user_stats": self._engineer.get_user_stats(txn.get("user_id", txn.get("nameOrig", "UNKNOWN"))),
        }
        self.send(KAFKA_PREDICTIONS_TOPIC, value=prediction, key=prediction["user_id"])

        if prediction["is_fraud"] or prediction["risk_score"] > 72:
            alert = {
                "alert_id": txn.get("transaction_id", "UNKNOWN"),
                "transaction_id": txn.get("transaction_id"),
                "user_id": prediction["user_id"],
                "fraud_type": txn.get("fraud_type", "Suspicious"),
                "risk_score": prediction["risk_score"],
                "merchant": txn.get("merchant", "N/A"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "message": f"HIGH RISK: risk_score={prediction['risk_score']} for {prediction['user_id']}"
            }
            self.send(KAFKA_ALERT_TOPIC, value=alert, key=prediction["user_id"])

        return prediction


def start_kafka_consumer(ensemble=None, engineer=None, broker=KAFKA_BROKER, interval_ms=100):
    client = KafkaClient(broker)
    if ensemble:
        client._ensemble = ensemble
    if engineer:
        client._engineer = engineer

    consumer = KafkaConsumer(
        KAFKA_RAW_TOPIC,
        bootstrap_servers=broker,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda k: k.decode("utf-8") if k else None,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id="sentinel-predictor",
    )

    for msg in consumer:
        try:
            client.predict_and_publish(msg.value)
        except Exception as e:
            print(f"[KafkaConsumer] Error processing message: {e}")


def run_kafka_consumer_background(ensemble=None, engineer=None):
    thread = threading.Thread(
        target=start_kafka_consumer,
        args=(ensemble, engineer),
        daemon=True,
    )
    thread.start()
    return thread
