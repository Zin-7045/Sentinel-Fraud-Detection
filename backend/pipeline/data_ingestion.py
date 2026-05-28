import json
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

from backend.config import KAFKA_RAW_TOPIC, KAFKA_ALERT_TOPIC

MERCHANTS = ["TechMart Pro", "GlobalPay", "SwiftShop", "NexCommerce", "PayHub", "CryptoXchange", "LuxuryGoods", "BetaPay"]
REGIONS = ["NA-EAST", "EU-WEST", "APAC", "LATAM", "ME-AF", "NA-WEST"]
CHANNELS = ["WEB", "MOBILE", "ATM", "POS", "API"]
FRAUD_TYPES = ["Card Skimming", "Account Takeover", "Synthetic ID", "Money Mule", "Phishing", "CNP Fraud"]
STATUSES = ["FLAGGED", "REVIEWING", "CONFIRMED", "CLEARED", "BLOCKED"]


class TransactionProducer:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.counter = 0

    def _rand(self) -> float:
        self.seed = (self.seed * 9301 + 49297) % 233280
        return self.seed / 233280

    def generate(self) -> Dict:
        self.counter += 1
        amount = round(self._rand() * 50000 + 0.5, 2)
        risk_score = min(99, int(self._rand() * 100 + (20 if amount > 300 else 0)))
        is_fraud = risk_score > 72 or self._rand() < 0.06
        fraud_type = random.choice(FRAUD_TYPES) if is_fraud else None

        return {
            "transaction_id": f"TXN-{str(self.counter).zfill(7)}",
            "timestamp": (datetime.utcnow() - timedelta(seconds=int(self._rand() * 3600))).isoformat(),
            "amount": amount,
            "merchant": random.choice(MERCHANTS),
            "region": random.choice(REGIONS),
            "channel": random.choice(CHANNELS),
            "fraud_type": fraud_type,
            "risk_score": risk_score,
            "status": random.choice(STATUSES),
            "user_id": f"USR-{str(random.randint(1, 9999)).zfill(4)}",
            "is_fraud": is_fraud,
            "latitude": round((self._rand() - 0.5) * 160, 4),
            "longitude": round((self._rand() - 0.5) * 360, 4),
            "device_id": str(uuid.uuid4())[:8],
            "ip_address": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "processing_ms": int(self._rand() * 120 + 8),
        }

    def stream_to_kafka(self, kafka_producer: Optional[callable] = None, interval_ms: int = 500):
        while True:
            txn = self.generate()
            msg = json.dumps(txn)
            if kafka_producer:
                kafka_producer(KAFKA_RAW_TOPIC, msg)
            else:
                yield msg
            if txn["is_fraud"] and txn["risk_score"] > 80:
                alert = json.dumps({
                    "alert_id": str(uuid.uuid4())[:8],
                    "transaction_id": txn["transaction_id"],
                    "fraud_type": txn["fraud_type"],
                    "risk_score": txn["risk_score"],
                    "merchant": txn["merchant"],
                    "user_id": txn["user_id"],
                    "region": txn["region"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": f"HIGH RISK: {txn['fraud_type']} detected on {txn['merchant']}"
                })
                if kafka_producer:
                    kafka_producer(KAFKA_ALERT_TOPIC, alert)
                else:
                    yield alert
            time.sleep(interval_ms / 1000)
