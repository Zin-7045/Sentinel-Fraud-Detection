# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
# ---

# %% [markdown]
# # Sentinel BDA — Exploratory Data Analysis
#
# ## Fraud Detection Transaction Dataset
#
# This notebook performs EDA on synthetic transaction data to understand:
# - Distribution of transaction amounts
# - Fraud rate by region, channel, merchant
# - Risk score distributions
# - Temporal patterns in fraud activity

# %% imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sys
sys.path.append("..")

from backend.pipeline.data_ingestion import TransactionProducer

sns.set_theme(style="darkgrid", palette="viridis")
plt.rcParams.update({"figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
                      "text.color": "#e6edf3", "axes.labelcolor": "#8b949e",
                      "xtick.color": "#6e7681", "ytick.color": "#6e7681",
                      "grid.color": "#21262d", "figure.figsize": (14, 6)})

# %% generate synthetic data
producer = TransactionProducer(seed=42)
transactions = [producer.generate() for _ in range(5000)]
df = pd.DataFrame(transactions)
df["timestamp"] = pd.to_datetime(df["timestamp"])
print(f"Generated {len(df)} transactions")
print(f"Fraud rate: {df['is_fraud'].mean()*100:.2f}%")

# %% basic stats
print("\n=== BASIC STATS ===")
print(df[["amount", "risk_score", "processing_ms"]].describe())

print("\n=== FRAUD TYPE DISTRIBUTION ===")
print(df[df["is_fraud"]]["fraud_type"].value_counts())

print("\n=== CHANNEL DISTRIBUTION ===")
print(df["channel"].value_counts())

print("\n=== REGION DISTRIBUTION ===")
print(df["region"].value_counts())

# %% amount distribution
fig, axes = plt.subplots(1, 2)
axes[0].hist(df["amount"], bins=50, color="#4cc9f0", alpha=0.7, edgecolor="none")
axes[0].set_title("Transaction Amount Distribution", color="#e6edf3")
axes[0].set_xlabel("Amount ($)")
axes[0].set_ylabel("Frequency")

clean = df[~df["is_fraud"]]["amount"]
fraud = df[df["is_fraud"]]["amount"]
axes[1].hist(clean, bins=50, alpha=0.6, label="Clean", color="#00f5d4")
axes[1].hist(fraud, bins=50, alpha=0.6, label="Fraud", color="#f72585")
axes[1].set_title("Amount: Clean vs Fraud", color="#e6edf3")
axes[1].set_xlabel("Amount ($)")
axes[1].legend()
plt.tight_layout()
plt.show()

# %% fraud rate by region and channel
fig, axes = plt.subplots(1, 2)
region_rate = df.groupby("region")["is_fraud"].mean().sort_values()
axes[0].barh(region_rate.index, region_rate.values * 100, color="#f72585", alpha=0.7)
axes[0].set_title("Fraud Rate by Region", color="#e6edf3")
axes[0].set_xlabel("Fraud Rate (%)")

channel_rate = df.groupby("channel")["is_fraud"].mean().sort_values()
axes[1].barh(channel_rate.index, channel_rate.values * 100, color="#4cc9f0", alpha=0.7)
axes[1].set_title("Fraud Rate by Channel", color="#e6edf3")
axes[1].set_xlabel("Fraud Rate (%)")
plt.tight_layout()
plt.show()

# %% risk score analysis
fig, axes = plt.subplots(1, 2)
axes[0].hist(df[~df["is_fraud"]]["risk_score"], bins=30, alpha=0.6, label="Clean", color="#00f5d4")
axes[0].hist(df[df["is_fraud"]]["risk_score"], bins=30, alpha=0.6, label="Fraud", color="#f72585")
axes[0].set_title("Risk Score Distribution", color="#e6edf3")
axes[0].set_xlabel("Risk Score")
axes[0].legend()

axes[1].scatter(df["amount"], df["risk_score"], c=df["is_fraud"].map({True: "#f72585", False: "#4cc9f0"}),
                alpha=0.4, s=10)
axes[1].set_title("Amount vs Risk Score", color="#e6edf3")
axes[1].set_xlabel("Amount ($)")
axes[1].set_ylabel("Risk Score")
plt.tight_layout()
plt.show()

# %% temporal patterns
df["hour"] = df["timestamp"].dt.hour
fraud_by_hour = df[df["is_fraud"]].groupby("hour").size()
all_by_hour = df.groupby("hour").size()
rate_by_hour = (fraud_by_hour / all_by_hour * 100).fillna(0)

fig, ax = plt.subplots()
ax.plot(rate_by_hour.index, rate_by_hour.values, color="#f72585", marker="o", linewidth=2)
ax.fill_between(rate_by_hour.index, rate_by_hour.values, alpha=0.2, color="#f72585")
ax.set_title("Fraud Rate by Hour of Day", color="#e6edf3")
ax.set_xlabel("Hour")
ax.set_ylabel("Fraud Rate (%)")
ax.set_xticks(range(24))
plt.show()

# %% merchant risk
merchant_stats = df.groupby("merchant").agg(
    total_txns=("transaction_id", "count"),
    fraud_count=("is_fraud", "sum"),
    avg_risk=("risk_score", "mean"),
    avg_amount=("amount", "mean")
).assign(fraud_rate=lambda x: x["fraud_count"] / x["total_txns"] * 100).sort_values("fraud_rate", ascending=False)

print("\n=== MERCHANT RISK RANKING ===")
print(merchant_stats)

# %% correlation analysis
numeric_cols = ["amount", "risk_score", "processing_ms", "is_fraud"]
corr = df[numeric_cols].corr()
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
ax.set_xticks(range(len(numeric_cols)))
ax.set_yticks(range(len(numeric_cols)))
ax.set_xticklabels(numeric_cols, rotation=45)
ax.set_yticklabels(numeric_cols)
plt.colorbar(im)
plt.title("Feature Correlation Matrix", color="#e6edf3")
plt.show()
