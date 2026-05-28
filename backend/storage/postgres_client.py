import psycopg2
import pandas as pd
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from backend.config import POSTGRES_DSN


class PostgresClient:
    def __init__(self, dsn: str = POSTGRES_DSN):
        self.dsn = dsn
        self.conn: Optional[psycopg2.extensions.connection] = None

    @contextmanager
    def cursor(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.dsn)
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def insert(self, table: str, data: Dict[str, Any]):
        cols = ", ".join(data.keys())
        placeholders = ", ".join([f"%({k})s" for k in data.keys()])
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self.cursor() as cur:
            cur.execute(query, data)

    def bulk_insert(self, table: str, records: List[Dict[str, Any]]):
        if not records:
            return
        cols = ", ".join(records[0].keys())
        placeholders = ", ".join([f"%({k})s" for k in records[0].keys()])
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self.cursor() as cur:
            for record in records:
                cur.execute(query, record)

    def query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute(sql, params or {})
            if cur.description:
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
            return []

    def query_df(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        rows = self.query(sql, params)
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def init_schema(self):
        schema = """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR(32) PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            user_id VARCHAR(32) NOT NULL,
            merchant VARCHAR(64) NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            channel VARCHAR(16) NOT NULL,
            region VARCHAR(16) NOT NULL,
            risk_score INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(16) NOT NULL,
            is_fraud BOOLEAN NOT NULL DEFAULT FALSE,
            fraud_type VARCHAR(32),
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(32) REFERENCES transactions(transaction_id),
            fraud_probability DECIMAL(6,4),
            risk_score INTEGER,
            is_fraud BOOLEAN,
            model_scores TEXT,
            factors TEXT,
            timestamp TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(32) REFERENCES transactions(transaction_id),
            severity VARCHAR(16),
            message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_txns_timestamp ON transactions(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_txns_is_fraud ON transactions(is_fraud);
        CREATE INDEX IF NOT EXISTS idx_txns_risk ON transactions(risk_score);
        """
        with self.cursor() as cur:
            cur.execute(schema)

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
