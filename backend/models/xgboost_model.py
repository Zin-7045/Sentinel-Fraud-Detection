import numpy as np
import pandas as pd
import xgboost as xgb
import joblib
from typing import Optional, Dict, List
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import os

from backend.config import MODEL_PATH


class XGBoostFraudDetector:
    def __init__(self, scale_pos_weight: float = 5.0, n_estimators: int = 300):
        self.scale_pos_weight = scale_pos_weight
        self.n_estimators = n_estimators
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_columns = [
            "transaction_amount", "velocity_1h", "merchant_risk_score",
            "geo_anomaly_score", "device_fingerprint_match",
            "time_since_last_txn", "amount_vs_avg_30d", "channel_frequency_score",
            "hour_of_day", "day_of_week", "is_high_amount", "is_cross_border"
        ]
        self.metrics: Dict[str, float] = {}

    def _build_model(self):
        return xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=self.scale_pos_weight,
            eval_metric="auc",
            use_label_encoder=False,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=20,
        )

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None,
              y_val: Optional[np.ndarray] = None):
        self.model = self._build_model()
        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=False
        )
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        return self.model.predict_proba(X)[:, 1]

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        preds = self.predict(X_test)
        probs = self.predict_proba(X_test)
        self.metrics = {
            "accuracy": accuracy_score(y_test, preds),
            "precision": precision_score(y_test, preds),
            "recall": recall_score(y_test, preds),
            "f1_score": f1_score(y_test, preds),
            "auc_roc": roc_auc_score(y_test, probs),
        }
        return self.metrics

    def get_feature_importance(self) -> Dict[str, float]:
        if self.model is None:
            return {f: 1.0 / len(self.feature_columns) for f in self.feature_columns}
        importances = self.model.feature_importances_
        total = importances.sum()
        return {
            name: float(imp / total)
            for name, imp in zip(self.feature_columns, importances)
        }

    def save(self, path: Optional[str] = None):
        path = path or os.path.join(MODEL_PATH, "xgboost_fraud.pkl")
        joblib.dump({
            "model": self.model,
            "metrics": self.metrics,
            "feature_columns": self.feature_columns,
            "scale_pos_weight": self.scale_pos_weight
        }, path)

    def load(self, path: Optional[str] = None):
        path = path or os.path.join(MODEL_PATH, "xgboost_fraud.pkl")
        data = joblib.load(path)
        self.model = data["model"]
        self.metrics = data.get("metrics", {})
        self.feature_columns = data.get("feature_columns", self.feature_columns)
        self.scale_pos_weight = data.get("scale_pos_weight", self.scale_pos_weight)
        return self
