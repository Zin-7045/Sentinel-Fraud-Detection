# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
# ---

# %% [markdown]
# # Feature Engineering for Fraud Detection
#
# This notebook demonstrates the feature engineering pipeline used by Sentinel.

# %% imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys
sys.path.append("..")

from backend.pipeline.data_ingestion import TransactionProducer
from backend.pipeline.feature_engineering import FeatureEngineer

sns.set_theme(style="darkgrid")
plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
                      "text.color": "#e6edf3", "figure.figsize": (14, 6)})

# %% generate transactions
producer = TransactionProducer(seed=42)
txns = [producer.generate() for _ in range(2000)]
df = pd.DataFrame(txns)
print(f"Generated {len(df)} transactions, {df['is_fraud'].sum()} fraud")

# %% extract features
engineer = FeatureEngineer()
features = engineer.batch_transform(txns)
feature_df = features.copy()
feature_df["is_fraud"] = df["is_fraud"].values

print(f"\nFeature shape: {features.shape}")
print(f"\n=== FEATURE STATS ===")
print(feature_df.describe())

# %% visualize feature distributions
fig, axes = plt.subplots(3, 4, figsize=(16, 10))
axes = axes.flatten()
for i, col in enumerate(feature_df.columns[:12]):
    if col == "is_fraud":
        continue
    axes[i].hist(feature_df[col], bins=40, color="#4cc9f0", alpha=0.7, edgecolor="none")
    axes[i].set_title(col, color="#e6edf3", fontsize=10)
    axes[i].tick_params(colors="#6e7681", labelsize=8)
plt.tight_layout()
plt.show()

# %% fraud vs clean feature comparison
fig, axes = plt.subplots(3, 4, figsize=(16, 10))
axes = axes.flatten()
for i, col in enumerate(feature_df.columns[:12]):
    axes[i].hist(feature_df[~feature_df["is_fraud"]][col], bins=40, alpha=0.5,
                 label="Clean", color="#00f5d4")
    axes[i].hist(feature_df[feature_df["is_fraud"]][col], bins=40, alpha=0.5,
                 label="Fraud", color="#f72585")
    axes[i].set_title(col, color="#e6edf3", fontsize=10)
    axes[i].legend(fontsize=8)
    axes[i].tick_params(colors="#6e7681", labelsize=8)
plt.tight_layout()
plt.show()

# %% correlation with target
target_corr = feature_df.corr()["is_fraud"].sort_values(ascending=False)
print("\n=== FEATURE CORRELATION WITH FRAUD ===")
print(target_corr)

# feature importance bar chart
fig, ax = plt.subplots()
colors = ["#f72585" if abs(v) > 0.1 else "#4cc9f0" for v in target_corr.values]
ax.barh(target_corr.index, target_corr.values, color=colors, alpha=0.7)
ax.set_title("Feature Correlation with Fraud Target", color="#e6edf3")
ax.set_xlabel("Correlation")
plt.tight_layout()
plt.show()

# %% PCA for dimensionality reduction
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = scaler.fit_transform(features)

pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

fig, ax = plt.subplots()
ax.scatter(X_pca[~df["is_fraud"].values, 0], X_pca[~df["is_fraud"].values, 1],
           c="#4cc9f0", alpha=0.3, s=10, label="Clean")
ax.scatter(X_pca[df["is_fraud"].values, 0], X_pca[df["is_fraud"].values, 1],
           c="#f72585", alpha=0.6, s=15, label="Fraud")
ax.set_title("PCA Projection of Engineered Features", color="#e6edf3")
ax.legend()
print(f"\nExplained variance ratio: {pca.explained_variance_ratio_}")
plt.show()
