import pandas as pd
import numpy as np
from datetime import datetime
from typing import Generator, Dict, List, Optional
import json

from backend.config import KAFKA_RAW_TOPIC, KAFKA_ENRICHED_TOPIC
from backend.storage.postgres_client import PostgresClient
from backend.storage.redis_cache import RedisCache
from backend.storage.mongodb_logger import MongoLogger


class ETLPipeline:
    def __init__(self, pg: PostgresClient, redis: RedisCache, mongo: MongoLogger):
        self.pg = pg
        self.redis = redis
        self.mongo = mongo
        self.batch_buffer: List[Dict] = []
        self.batch_size = 100

    def extract(self, stream: Generator[Dict, None, None]) -> Generator[Dict, None, None]:
        for txn in stream:
            self.batch_buffer.append(txn)
            if len(self.batch_buffer) >= self.batch_size:
                yield self.batch_buffer[:]
                self.batch_buffer.clear()

    def transform(self, batch: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(batch)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["amount_log"] = np.log1p(df["amount"])
        df["risk_category"] = pd.cut(
            df["risk_score"],
            bins=[0, 30, 60, 80, 100],
            labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        )
        return df

    def load_postgres(self, df: pd.DataFrame):
        records = df[[
            "transaction_id", "timestamp", "user_id", "merchant",
            "amount", "channel", "region", "risk_score", "status", "is_fraud"
        ]].to_dict(orient="records")
        self.pg.bulk_insert("transactions", records)

    def load_redis(self, df: pd.DataFrame):
        fraud_count = int(df["is_fraud"].sum())
        total = len(df)
        avg_risk = float(df["risk_score"].mean())
        self.redis.set("etl:fraud_count", self.redis.get("etl:fraud_count", 0) + fraud_count)
        self.redis.set("etl:total_count", self.redis.get("etl:total_count", 0) + total)
        self.redis.set("etl:avg_risk", avg_risk, ttl=3600)

    def load_mongo(self, df: pd.DataFrame):
        alerts = df[df["is_fraud"] == True].to_dict(orient="records")
        if alerts:
            self.mongo.insert_many("fraud_alerts", alerts)

    def run(self, stream: Generator[Dict, None, None]):
        for batch in self.extract(stream):
            df = self.transform(batch)
            self.load_postgres(df)
            self.load_redis(df)
            self.load_mongo(df)

    def backfill(self, start_date: str, end_date: str):
        query = """
            SELECT * FROM transactions
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp
        """
        df = self.pg.query(query, (start_date, end_date))
        df = self.transform(df.to_dict(orient="records"))
        self.load_mongo(df)
        return len(df)
