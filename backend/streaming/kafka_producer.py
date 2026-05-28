import json
import time
from kafka import KafkaProducer as KProducer
from typing import Callable, Optional

from backend.config import KAFKA_BROKER, KAFKA_RAW_TOPIC, KAFKA_ALERT_TOPIC
from backend.pipeline.data_ingestion import TransactionProducer


class FraudKafkaProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BROKER):
        self.producer = KProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
            batch_size=16384,
            linger_ms=10,
        )
        self.txn_producer = TransactionProducer()

    def send_transaction(self, txn: dict, topic: str = KAFKA_RAW_TOPIC):
        future = self.producer.send(topic, value=txn)
        future.add_callback(lambda m: None)
        future.add_errback(lambda e: print(f"Kafka send error: {e}"))

    def send_alert(self, txn: dict):
        alert = {
            "alert_id": str(hash(txn["transaction_id"])),
            "transaction_id": txn["transaction_id"],
            "fraud_type": txn["fraud_type"],
            "risk_score": txn["risk_score"],
            "merchant": txn["merchant"],
            "user_id": txn["user_id"],
            "region": txn["region"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": f"HIGH RISK: {txn['fraud_type']} detected on {txn['merchant']}"
        }
        self.producer.send(KAFKA_ALERT_TOPIC, value=alert)

    def stream_continuous(self, interval_ms: int = 500):
        while True:
            txn = self.txn_producer.generate()
            self.send_transaction(txn)
            if txn["is_fraud"] and txn["risk_score"] > 80:
                self.send_alert(txn)
            self.producer.flush()
            time.sleep(interval_ms / 1000)

    def close(self):
        self.producer.flush()
        self.producer.close()


class SimpleFileProducer:
    def __init__(self, output_file: str = "transactions.jsonl"):
        self.output_file = output_file
        self.txn_producer = TransactionProducer()

    def stream_to_file(self, count: int = 100, interval_ms: int = 200):
        with open(self.output_file, "w") as f:
            for i in range(count):
                txn = self.txn_producer.generate()
                f.write(json.dumps(txn) + "\n")
                time.sleep(interval_ms / 1000)
