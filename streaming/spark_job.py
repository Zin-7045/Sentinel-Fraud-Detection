import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, sum as _sum, avg, count, when, window, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, BooleanType
)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "bda-kafka-1:9092")
RAW_TOPIC = "txn.raw"
PREDICTIONS_TOPIC = "model.predictions"

txn_schema = StructType([
    StructField("transaction_id", StringType()),
    StructField("timestamp", StringType()),
    StructField("amount", DoubleType()),
    StructField("merchant", StringType()),
    StructField("region", StringType()),
    StructField("channel", StringType()),
    StructField("fraud_type", StringType()),
    StructField("risk_score", IntegerType()),
    StructField("status", StringType()),
    StructField("user_id", StringType()),
    StructField("is_fraud", BooleanType()),
    StructField("latitude", DoubleType()),
    StructField("longitude", DoubleType()),
    StructField("device_id", StringType()),
    StructField("ip_address", StringType()),
    StructField("processing_ms", IntegerType()),
])

spark = SparkSession.builder \
    .appName("SentinelSparkStreaming") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", RAW_TOPIC) \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

parsed_df = raw_df.select(
    from_json(col("value").cast("string"), txn_schema).alias("data")
).select("data.*")

parsed_df = parsed_df.withColumn("event_time", to_timestamp(col("timestamp")))

aggregated_df = parsed_df \
    .withWatermark("event_time", "30 seconds") \
    .groupBy(
        window(col("event_time"), "30 seconds", "15 seconds"),
        col("region"),
        col("channel"),
    ) \
    .agg(
        count("*").alias("total_transactions"),
        _sum("amount").alias("total_amount"),
        avg("amount").alias("avg_amount"),
        _sum(when(col("is_fraud") == True, 1).otherwise(0)).alias("fraud_count"),
        avg(when(col("is_fraud") == True, col("amount")).otherwise(0)).alias("avg_fraud_amount"),
        avg("risk_score").alias("avg_risk_score"),
    )

result_df = aggregated_df.selectExpr("to_json(struct(*)) AS value")

query = result_df.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("topic", PREDICTIONS_TOPIC) \
    .option("checkpointLocation", "/tmp/spark-checkpoint") \
    .outputMode("update") \
    .start()

console_query = parsed_df.select(
    "transaction_id", "user_id", "amount", "merchant",
    "region", "channel", "risk_score", "is_fraud"
).writeStream \
    .outputMode("append") \
    .format("console") \
    .trigger(processingTime="10 seconds") \
    .start()

query.awaitTermination()
