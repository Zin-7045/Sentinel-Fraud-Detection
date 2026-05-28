import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest as SKIsolationForest
import joblib
from typing import Optional, List, Dict
import os

from backend.config import MODEL_PATH


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.05, n_estimators: int = 200):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model: Optional[SKIsolationForest] = None
        self.feature_columns = [
            "transaction_amount", "velocity_1h", "merchant_risk_score",
            "geo_anomaly_score", "device_fingerprint_match",
            "time_since_last_txn", "amount_vs_avg_30d", "channel_frequency_score",
            "hour_of_day", "day_of_week", "is_high_amount", "is_cross_border"
        ]

    def train(self, X: np.ndarray):
        self.model = SKIsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
            max_samples="auto",
            bootstrap=False,
        )
        self.model.fit(X)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        preds = self.model.predict(X)
        return np.where(preds == -1, 1, 0)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        scores = self.model.score_samples(X)
        probas = 1 - (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
        return np.clip(probas, 0, 1)

    def anomaly_score(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        return -self.model.score_samples(X)

    def save(self, path: Optional[str] = None):
        path = path or os.path.join(MODEL_PATH, "isolation_forest.pkl")
        joblib.dump({
            "model": self.model,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "feature_columns": self.feature_columns
        }, path)

    def load(self, path: Optional[str] = None):
        path = path or os.path.join(MODEL_PATH, "isolation_forest.pkl")
        data = joblib.load(path)
        self.model = data["model"]
        self.contamination = data["contamination"]
        self.n_estimators = data["n_estimators"]
        self.feature_columns = data["feature_columns"]
        return self

    def train_on_dataframe(self, df: pd.DataFrame) -> "IsolationForestDetector":
        X = df[self.feature_columns].values
        return self.train(X)

    def get_feature_importance(self) -> Dict[str, float]:
        return {f: 1.0 / len(self.feature_columns) for f in self.feature_columns}
