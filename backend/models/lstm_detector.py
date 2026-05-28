import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple
import os
import joblib

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, Input
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.utils import to_categorical
    _HAS_TF = True
except ImportError:
    _HAS_TF = False

from backend.config import MODEL_PATH


class LSTMSequenceDetector:
    def __init__(self, sequence_length: int = 10, n_features: int = 12):
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.model: Optional['Sequential'] = None
        self.feature_columns = [
            "transaction_amount", "velocity_1h", "merchant_risk_score",
            "geo_anomaly_score", "device_fingerprint_match",
            "time_since_last_txn", "amount_vs_avg_30d", "channel_frequency_score",
            "hour_of_day", "day_of_week", "is_high_amount", "is_cross_border"
        ]
        if not _HAS_TF:
            print("[WARN] TensorFlow not installed. LSTM detector disabled.")

    def build_model(self):
        if not _HAS_TF:
            raise ImportError("TensorFlow is not installed. Cannot build LSTM model.")
        model = Sequential([
            Input(shape=(self.sequence_length, self.n_features)),
            LSTM(128, return_sequences=True),
            BatchNormalization(),
            Dropout(0.3),
            LSTM(64, return_sequences=False),
            BatchNormalization(),
            Dropout(0.3),
            Dense(32, activation="relu"),
            BatchNormalization(),
            Dropout(0.2),
            Dense(1, activation="sigmoid"),
        ])
        model.compile(
            optimizer=Adam(learning_rate=1e-3),
            loss="binary_crossentropy",
            metrics=["accuracy", "precision", "recall"]
        )
        self.model = model
        return model

    def create_sequences(self, X: np.ndarray, y: Optional[np.ndarray] = None
                         ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        sequences, labels = [], []
        for i in range(len(X) - self.sequence_length):
            sequences.append(X[i:i + self.sequence_length])
            if y is not None:
                labels.append(y[i + self.sequence_length])
        if y is not None:
            return np.array(sequences), np.array(labels)
        return np.array(sequences), None

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None,
              y_val: Optional[np.ndarray] = None,
              epochs: int = 50, batch_size: int = 64):
        if not _HAS_TF:
            raise ImportError("TensorFlow is not installed. Cannot train LSTM model.")
        if self.model is None:
            self.build_model()

        X_seq, y_seq = self.create_sequences(X_train, y_train)
        validation_data = None
        if X_val is not None and y_val is not None:
            Xv_seq, yv_seq = self.create_sequences(X_val, y_val)
            validation_data = (Xv_seq, yv_seq)

        callbacks = [
            EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-7)
        ]

        history = self.model.fit(
            X_seq, y_seq,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            return np.zeros(len(X))
        X_seq, _ = self.create_sequences(X)
        raw = self.model.predict(X_seq, verbose=0).flatten()
        padded = np.zeros(len(X))
        padded[self.sequence_length:] = raw
        return (padded > 0.5).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            return np.zeros(len(X))
        X_seq, _ = self.create_sequences(X)
        raw = self.model.predict(X_seq, verbose=0).flatten()
        padded = np.zeros(len(X))
        padded[self.sequence_length:] = raw
        return padded

    def save(self, path: Optional[str] = None):
        if not _HAS_TF:
            raise ImportError("TensorFlow is not installed. Cannot save LSTM model.")
        path = path or os.path.join(MODEL_PATH, "lstm_fraud.keras")
        meta_path = path.replace(".keras", "_meta.pkl")
        self.model.save(path)
        joblib.dump({
            "sequence_length": self.sequence_length,
            "n_features": self.n_features,
            "feature_columns": self.feature_columns
        }, meta_path)

    def load(self, path: Optional[str] = None):
        if not _HAS_TF:
            raise ImportError("TensorFlow is not installed. Cannot load LSTM model.")
        path = path or os.path.join(MODEL_PATH, "lstm_fraud.keras")
        meta_path = path.replace(".keras", "_meta.pkl")
        self.model = load_model(path)
        meta = joblib.load(meta_path)
        self.sequence_length = meta["sequence_length"]
        self.n_features = meta["n_features"]
        self.feature_columns = meta.get("feature_columns", self.feature_columns)
        return self
