# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
# ---

# %% [markdown]
# # Model Training & Evaluation
#
# Training Isolation Forest, XGBoost, and LSTM models for fraud detection.

# %% imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.append("..")

from backend.pipeline.data_ingestion import TransactionProducer
from backend.pipeline.feature_engineering import FeatureEngineer
from backend.models.isolation_forest import IsolationForestDetector
from backend.models.xgboost_model import XGBoostFraudDetector
from backend.models.ensemble import FraudEnsemble

sns.set_theme(style="darkgrid")
plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
                      "text.color": "#e6edf3", "figure.figsize": (14, 6)})

# %% generate dataset
producer = TransactionProducer(seed=42)
txns = [producer.generate() for _ in range(10000)]
df = pd.DataFrame(txns)
print(f"Total: {len(df)}, Fraud: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.1f}%)")

# %% feature engineering
engineer = FeatureEngineer()
X = engineer.batch_transform(txns)
y = df["is_fraud"].values.astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# %% ISOLATION FOREST
print("\n=== ISOLATION FOREST ===")
if_model = IsolationForestDetector(contamination=df["is_fraud"].mean())
if_model.train(X_train.values)
if_preds = if_model.predict(X_test.values)
if_probs = if_model.predict_proba(X_test.values)
if_fpr, if_tpr, _ = roc_curve(y_test, if_probs)
if_auc = auc(if_fpr, if_tpr)

print(classification_report(y_test, if_preds, target_names=["Clean", "Fraud"]))
print(f"AUC-ROC: {if_auc:.4f}")

# %% XGBOOST
print("\n=== XGBOOST ===")
xgb_model = XGBoostFraudDetector(scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum())
xgb_model.train(X_train.values, y_train, X_test.values, y_test)
xgb_preds = xgb_model.predict(X_test.values)
xgb_probs = xgb_model.predict_proba(X_test.values)
xgb_metrics = xgb_model.evaluate(X_test.values, y_test)
xgb_fpr, xgb_tpr, _ = roc_curve(y_test, xgb_probs)
xgb_auc = auc(xgb_fpr, xgb_tpr)

print(classification_report(y_test, xgb_preds, target_names=["Clean", "Fraud"]))
for k, v in xgb_metrics.items():
    print(f"{k}: {v:.4f}")

# %% feature importance
importance = xgb_model.get_feature_importance()
fig, ax = plt.subplots()
feats = list(importance.keys())
vals = list(importance.values())
ax.barh(feats, vals, color="#4cc9f0", alpha=0.7)
ax.set_title("XGBoost Feature Importance", color="#e6edf3")
ax.set_xlabel("Importance")
plt.tight_layout()
plt.show()

# %% COMPARISON ROC CURVES
fig, ax = plt.subplots()
ax.plot(if_fpr, if_tpr, label=f"Isolation Forest (AUC = {if_auc:.3f})", color="#4cc9f0", lw=2)
ax.plot(xgb_fpr, xgb_tpr, label=f"XGBoost (AUC = {xgb_auc:.3f})", color="#f72585", lw=2)
ax.plot([0, 1], [0, 1], "k--", alpha=0.3, color="#6e7681")
ax.set_xlabel("False Positive Rate", color="#e6edf3")
ax.set_ylabel("True Positive Rate", color="#e6edf3")
ax.set_title("ROC Curves — Fraud Detection Models", color="#e6edf3")
ax.legend()
plt.tight_layout()
plt.show()

# %% CONFUSION MATRICES
fig, axes = plt.subplots(1, 2)
for ax, (name, preds) in zip(axes, [("Isolation Forest", if_preds), ("XGBoost", xgb_preds)]):
    cm = confusion_matrix(y_test, preds)
    sns.heatmap(cm, annot=True, fmt="d", cmap="viridis", ax=ax,
                xticklabels=["Clean", "Fraud"], yticklabels=["Clean", "Fraud"])
    ax.set_title(f"{name}", color="#e6edf3")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
plt.tight_layout()
plt.show()

# %% ENSEMBLE EVALUATION
print("\n=== ENSEMBLE EVALUATION ===")
ensemble = FraudEnsemble()
ensemble.isolation_forest = if_model
ensemble.xgboost = xgb_model
ensemble.models_loaded = True

y_probs = []
for i in range(len(X_test)):
    result = ensemble.predict(X_test.values[i])
    y_probs.append(result.fraud_probability)
y_probs = np.array(y_probs)
y_ensemble_preds = (y_probs > 0.5).astype(int)

ens_fpr, ens_tpr, _ = roc_curve(y_test, y_probs)
ens_auc = auc(ens_fpr, ens_tpr)

print(classification_report(y_test, y_ensemble_preds, target_names=["Clean", "Fraud"]))
print(f"Ensemble AUC-ROC: {ens_auc:.4f}")

fig, ax = plt.subplots()
ax.plot(if_fpr, if_tpr, label=f"Isolation Forest ({if_auc:.3f})", color="#4cc9f0", lw=2)
ax.plot(xgb_fpr, xgb_tpr, label=f"XGBoost ({xgb_auc:.3f})", color="#f72585", lw=2)
ax.plot(ens_fpr, ens_tpr, label=f"Ensemble ({ens_auc:.3f})", color="#00f5d4", lw=3)
ax.plot([0, 1], [0, 1], "k--", alpha=0.3, color="#6e7681")
ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curves Comparison", color="#e6edf3")
ax.legend()
plt.show()

# %% SAVE MODELS
if_model.save()
xgb_model.save()
print("\nModels saved to backend/models/artifacts/")
