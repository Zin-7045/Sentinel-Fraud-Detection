import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict


class FeatureEngineer:
    def __init__(self):
        self.user_txn_history = defaultdict(list)
        self.merchant_scores = defaultdict(lambda: 0.5)
        self.velocity_window = timedelta(hours=1)

    def compute_velocity_1h(self, user_id: str, timestamp: datetime) -> int:
        cutoff = timestamp - self.velocity_window
        self.user_txn_history[user_id] = [
            t for t in self.user_txn_history[user_id] if t > cutoff
        ]
        return len(self.user_txn_history[user_id])

    def compute_merchant_risk(self, merchant: str, default: float = 0.5) -> float:
        return self.merchant_scores.get(merchant, default)

    def compute_geo_anomaly(self, lat: float, lng: float,
                            user_geo_history: List[tuple]) -> float:
        if not user_geo_history:
            return 0.0
        avg_lat = np.mean([g[0] for g in user_geo_history])
        avg_lng = np.mean([g[1] for g in user_geo_history])
        dist = np.sqrt((lat - avg_lat)**2 + (lng - avg_lng)**2)
        return min(1.0, dist / 50.0)

    def compute_time_since_last_txn(self, user_id: str,
                                    current_time: datetime) -> float:
        history = self.user_txn_history[user_id]
        if len(history) < 2:
            return 1.0
        last_txn = history[-2]
        seconds_since = (current_time - last_txn).total_seconds()
        return min(1.0, seconds_since / 86400.0)

    def compute_amount_vs_avg_30d(self, user_id: str,
                                   amount: float) -> float:
        history = self.user_txn_history[user_id]
        if len(history) < 5:
            return 0.0
        avg_amount = np.mean(history)
        if avg_amount == 0:
            return 0.0
        return min(1.0, abs(amount - avg_amount) / avg_amount)

    def compute_channel_frequency(self, user_id: str,
                                   channel: str) -> float:
        history = self.user_txn_history[user_id]
        if not history:
            return 0.0
        channel_count = sum(1 for t in history if t.channel == channel)
        return channel_count / len(history)

    def device_fingerprint_match(self, device_id: str,
                                 known_devices: set) -> float:
        return 0.0 if device_id in known_devices else 0.8

    def extract_features(self, txn: Dict) -> np.ndarray:
        timestamp = datetime.fromisoformat(txn["timestamp"])
        user_id = txn["user_id"]

        velocity = self.compute_velocity_1h(user_id, timestamp)
        merchant_risk = self.compute_merchant_risk(txn["merchant"])
        geo_anomaly = self.compute_geo_anomaly(txn["latitude"],
                                                txn["longitude"], [])
        time_since = self.compute_time_since_last_txn(user_id, timestamp)
        amount_ratio = self.compute_amount_vs_avg_30d(user_id, txn["amount"])
        channel_freq = self.compute_channel_frequency(user_id, txn["channel"])
        device_score = self.device_fingerprint_match(txn["device_id"], set())

        hour = timestamp.hour
        amount_high = 1.0 if txn["amount"] > 500 else 0.0
        cross_border = 1.0 if txn["region"] in ["APAC", "LATAM", "ME-AF"] else 0.0

        self.user_txn_history[user_id].append(timestamp)

        return np.array([
            txn["amount"], velocity, merchant_risk,
            geo_anomaly, device_score,
            time_since, amount_ratio, channel_freq,
            hour, timestamp.weekday(), amount_high, cross_border
        ], dtype=np.float32)

    def batch_transform(self, transactions: List[Dict]) -> pd.DataFrame:
        features = [self.extract_features(t) for t in transactions]
        cols = [
            "transaction_amount", "velocity_1h", "merchant_risk_score",
            "geo_anomaly_score", "device_fingerprint_match",
            "time_since_last_txn", "amount_vs_avg_30d", "channel_frequency_score",
            "hour_of_day", "day_of_week", "is_high_amount", "is_cross_border"
        ]
        return pd.DataFrame(features, columns=cols)
