from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum, avg, count, when, desc

CSV_PATH = "/data/dataset.csv"

spark = SparkSession.builder \
    .appName("SentinelBatchAnalysis") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

df = spark.read \
    .option("header", "true") \
    .option("inferSchema", "true") \
    .csv(CSV_PATH) \
    .cache()

total = df.count()
fraud_count = df.filter(col("isFraud") == 1).count()
print(f"\n{'='*60}")
print(f"  SENTINEL — Spark Batch Analysis")
print(f"{'='*60}")
print(f"  Total transactions: {total:,}")
print(f"  Fraud transactions: {fraud_count:,}")
print(f"  Fraud rate:        {fraud_count/max(total,1)*100:.4f}%")
print(f"{'='*60}")

print("\n  Fraud amount stats:")
fraud_df = df.filter(col("isFraud") == 1)
fraud_df.select(
    avg("amount").alias("avg_fraud_amount"),
    _sum("amount").alias("total_fraud_amount"),
    count("*").alias("count")
).show(truncate=False)

print("  Top 5 fraud types by count:")
df.filter(col("isFraud") == 1) \
    .groupBy("type") \
    .agg(count("*").alias("count"), avg("amount").alias("avg_amount")) \
    .orderBy(desc("count")) \
    .show(5, truncate=False)

print("  Top 10 users by transaction count:")
df.groupBy("nameOrig") \
    .agg(
        count("*").alias("txn_count"),
        _sum("amount").alias("total_amount"),
        _sum(when(col("isFraud") == 1, 1).otherwise(0)).alias("fraud_count")
    ) \
    .orderBy(desc("txn_count")) \
    .show(10, truncate=False)

print("  Fraud per transaction type:")
df.groupBy("type") \
    .agg(
        count("*").alias("total"),
        _sum(when(col("isFraud") == 1, 1).otherwise(0)).alias("fraud"),
    ) \
    .orderBy(desc("fraud")) \
    .show(truncate=False)

print(f"{'='*60}")
print(f"  Spark batch analysis complete!")
print(f"{'='*60}\n")

spark.stop()
