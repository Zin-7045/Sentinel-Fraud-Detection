from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum as _sum, desc

spark = SparkSession.builder \
    .appName("SentinelSparkDemo") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

csv_path = "/opt/bitnami/spark/data/dataset.csv"

print("\n" + "=" * 60)
print("  SENTINEL — Spark Structured Processing")
print("=" * 60)

columns = ["step", "type", "amount", "nameOrig", "oldbalanceOrg",
           "newbalanceOrig", "nameDest", "oldbalanceDest",
           "newbalanceDest", "isFraud", "isFlaggedFraud"]

df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(csv_path)

total = df.count()
fraud = df.filter(col("isFraud") == 1).count()
flagged = df.filter(col("isFlaggedFraud") == 1).count()

print(f"  Total transactions:  {total:,}")
print(f"  Fraud transactions:  {fraud:,} ({fraud/max(total,1)*100:.4f}%)")
print(f"  Flagged fraud:       {flagged:,}")
print(f"  Spark Workers:       1 (2 cores / 2 GiB)")
print()

print("  Top 5 fraud transaction types:")
df.filter(col("isFraud") == 1) \
    .groupBy("type") \
    .agg(count("*").alias("count")) \
    .orderBy(desc("count")) \
    .show(5, truncate=False)

print("  Fraud amount distribution:")
fraud_df = df.filter(col("isFraud") == 1)
fraud_df.select(
    _sum("amount").alias("total_fraud_amount"),
    (count("*") / total * 100).alias("fraud_pct")
).show(truncate=False)

print("=" * 60)
print("  Spark processing complete!")
print("=" * 60 + "\n")

spark.stop()
