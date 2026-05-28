from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, udf
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType, BooleanType

from backend.config import KAFKA_BROKER, SPARK_MASTER, KAFKA_RAW_TOPIC, KAFKA_ENRICHED_TOPIC

TXN_SCHEMA = StructType() \
    .add("transaction_id", StringType()) \
    .add("timestamp", StringType()) \
    .add("amount", DoubleType()) \
    .add("merchant", StringType()) \
    .add("region", StringType()) \
    .add("channel", StringType()) \
    .add("fraud_type", StringType()) \
    .add("risk_score", IntegerType()) \
    .add("status", StringType()) \
    .add("user_id", StringType()) \
    .add("is_fraud", BooleanType()) \
    .add("latitude", DoubleType()) \
    .add("longitude", DoubleType()) \
    .add("device_id", StringType()) \
    .add("ip_address", StringType()) \
    .add("processing_ms", IntegerType())


class SparkStreamProcessor:
    def __init__(self, app_name: str = "FraudDetectionStream"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master(SPARK_MASTER) \
            .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint") \
            .config("spark.sql.shuffle.partitions", "4") \
            .getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")

    def start_stream(self):
        raw_stream = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BROKER) \
            .option("subscribe", KAFKA_RAW_TOPIC) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()

        parsed = raw_stream.select(
            from_json(col("value").cast("string"), TXN_SCHEMA).alias("data")
        ).select("data.*")

        enriched = parsed.withColumn(
            "amount_category",
            when(col("amount") > 1000, "HIGH")
            .when(col("amount") > 300, "MEDIUM")
            .otherwise("LOW")
        ).withColumn(
            "is_high_amount", col("amount") > 500
        ).withColumn(
            "is_cross_border",
            when(col("region").rlike("^(APAC|LATAM|ME-AF)$"), True).otherwise(False)
        ).withColumn(
            "risk_level",
            when(col("risk_score") >= 80, "CRITICAL")
            .when(col("risk_score") >= 60, "HIGH")
            .when(col("risk_score") >= 30, "MEDIUM")
            .otherwise("LOW")
        )

        enriched \
            .selectExpr("to_json(struct(*)) AS value") \
            .writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BROKER) \
            .option("topic", KAFKA_ENRICHED_TOPIC) \
            .option("checkpointLocation", "/tmp/spark-enriched-checkpoint") \
            .outputMode("append") \
            .trigger(processingTime="5 seconds") \
            .start()

        fraud_count = enriched.filter(col("is_fraud") == True) \
            .groupBy("region", "fraud_type") \
            .count()

        query = fraud_count.writeStream \
            .outputMode("complete") \
            .format("console") \
            .trigger(processingTime="10 seconds") \
            .start()

        self.spark.streams.awaitAnyTermination()

    def process_batch(self, df):
        features = df.select(
            "transaction_amount", "velocity_1h", "merchant_risk_score",
            "geo_anomaly_score", "device_fingerprint_match",
            "time_since_last_txn", "amount_vs_avg_30d", "channel_frequency_score"
        )
        return features

    def stop(self):
        self.spark.stop()
