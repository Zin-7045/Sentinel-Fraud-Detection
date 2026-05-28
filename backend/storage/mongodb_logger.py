from typing import Optional, List, Dict, Any
from datetime import datetime
import pymongo
from pymongo.errors import ConnectionFailure

from backend.config import MONGO_URI, MONGO_DB


class MongoLogger:
    def __init__(self, uri: str = MONGO_URI, db_name: str = MONGO_DB):
        self.uri = uri
        self.db_name = db_name
        self.client: Optional[pymongo.MongoClient] = None
        self.db: Optional[pymongo.database.Database] = None
        self._connect()

    def _connect(self):
        try:
            self.client = pymongo.MongoClient(
                self.uri, serverSelectionTimeoutMS=3000
            )
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            self._ensure_indexes()
        except ConnectionFailure:
            self.db = None

    def _ensure_indexes(self):
        if self.db is None:
            return
        self.db.fraud_alerts.create_index("timestamp", expireAfterSeconds=604800)
        self.db.fraud_alerts.create_index("risk_score")
        self.db.fraud_alerts.create_index("transaction_id", unique=True, sparse=True)

    def insert(self, collection: str, document: Dict[str, Any]) -> Optional[str]:
        if self.db is None:
            return None
        doc = {**document, "created_at": datetime.utcnow()}
        result = self.db[collection].insert_one(doc)
        return str(result.inserted_id)

    def insert_many(self, collection: str, documents: List[Dict[str, Any]]):
        if self.db is None or not documents:
            return
        docs = [{**d, "created_at": datetime.utcnow()} for d in documents]
        self.db[collection].insert_many(docs, ordered=False)

    def find(self, collection: str, query: Dict = None,
             limit: int = 100, sort: list = None) -> List[Dict]:
        if self.db is None:
            return []
        query = query or {}
        sort = sort or [("created_at", -1)]
        return list(self.db[collection].find(query, {"_id": 0})
                    .sort(sort).limit(limit))

    def aggregate(self, collection: str, pipeline: list) -> List[Dict]:
        if self.db is None:
            return []
        return list(self.db[collection].aggregate(pipeline))

    def log_alert(self, txn_id: str, fraud_type: str, risk_score: int,
                  merchant: str, user_id: str, region: str, score: float):
        return self.insert("fraud_alerts", {
            "transaction_id": txn_id,
            "fraud_type": fraud_type,
            "risk_score": risk_score,
            "merchant": merchant,
            "user_id": user_id,
            "region": region,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def close(self):
        if self.client:
            self.client.close()
