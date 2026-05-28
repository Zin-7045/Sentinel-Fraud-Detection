import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from backend.models.isolation_forest import IsolationForestDetector
from backend.models.xgboost_model import XGBoostFraudDetector
from backend.models.lstm_detector import LSTMSequenceDetector


@dataclass
class EnsemblePrediction:
    fraud_probability: float
    is_fraud: bool
    risk_score: int
    model_scores: Dict[str, float]
    contributing_factors: List[str] = field(default_factory=list)


class FraudEnsemble:
    WEIGHTS = {
        "isolation_forest": 0.25,
        "xgboost": 0.45,
        "lstm": 0.30,
    }

    def __init__(self):
        self.isolation_forest = IsolationForestDetector()
        self.xgboost = XGBoostFraudDetector()
        self.lstm = LSTMSequenceDetector()
        self.models_loaded = False

    def load_models(self):
        try:
            self.isolation_forest.load()
            self.xgboost.load()
            try:
                self.lstm.load()
            except (ImportError, FileNotFoundError):
                pass
            self.models_loaded = True
        except FileNotFoundError:
            self.models_loaded = False

    def predict(self, X: np.ndarray) -> EnsemblePrediction:
        if not self.models_loaded:
            self.load_models()

        if not self.models_loaded or self.xgboost.model is None:
            return self._fallback_prediction(X)

        if X.ndim == 1:
            X = X.reshape(1, -1)

        # Isolation Forest score
        if_score = self.isolation_forest.predict_proba(X)[0] if self.isolation_forest.model else 0.5

        # XGBoost score
        xgb_score = self.xgboost.predict_proba(X)[0]

        # LSTM score (needs sequence)
        lstm_score = 0.0
        if self.lstm.model and len(X) >= self.lstm.sequence_length:
            lstm_score = float(self.lstm.predict_proba(X)[-1])

        weighted = (
            if_score * self.WEIGHTS["isolation_forest"] +
            xgb_score * self.WEIGHTS["xgboost"] +
            lstm_score * self.WEIGHTS["lstm"]
        )

        risk_score = min(99, int(weighted * 100))
        is_fraud = weighted > 0.5

        factors = []
        if if_score > 0.6:
            factors.append("AnomalyPattern")
        if xgb_score > 0.5:
            factors.append(f"XGBoost:{xgb_score:.2f}")
        if lstm_score > 0.5:
            factors.append("SequenceAnomaly")
        if risk_score > 80:
            factors.append("CriticalRisk")

        return EnsemblePrediction(
            fraud_probability=round(weighted, 4),
            is_fraud=is_fraud,
            risk_score=risk_score,
            model_scores={
                "isolation_forest": round(if_score, 4),
                "xgboost": round(xgb_score, 4),
                "lstm": round(lstm_score, 4),
            },
            contributing_factors=factors,
        )

    def predict_batch(self, X: np.ndarray) -> List[EnsemblePrediction]:
        return [self.predict(x.reshape(1, -1)) for x in X]

    def _fallback_prediction(self, X: np.ndarray) -> EnsemblePrediction:
        if X.ndim == 1:
            amount = X[0]
        else:
            amount = X[0, 0]
        fallback_score = min(1.0, amount / 1000.0)
        return EnsemblePrediction(
            fraud_probability=fallback_score,
            is_fraud=fallback_score > 0.5,
            risk_score=min(99, int(fallback_score * 100)),
            model_scores={"fallback": fallback_score},
            contributing_factors=["FallbackHeuristic"],
        )
