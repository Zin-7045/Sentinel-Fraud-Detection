from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when, window, count, avg
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType, BooleanType, TimestampType

from backend.config import KAFKA_BROKER, SPARK_MASTER

TXN_SCHEMA = StructType() \
    .add("transaction_id", StringType()) \
    .add("timestamp", TimestampType()) \
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


class SparkFraudStreaming:
    def __init__(self, app_name: str = "FraudDetectionSpark"):
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master(SPARK_MASTER) \
            .config("spark.sql.streaming.schemaInference", "true") \
            .config("spark.sql.shuffle.partitions", "4") \
            .getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")

    def read_from_kafka(self, topic: str):
        return self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BROKER) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()

    def parse_stream(self, df):
        return df.select(
            from_json(col("value").cast("string"), TXN_SCHEMA).alias("data")
        ).select("data.*")

    def fraud_aggregation(self, df):
        return df.filter(col("is_fraud") == True) \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window(col("timestamp"), "5 minutes"),
                col("region"),
                col("fraud_type")
            ).agg(
                count("*").alias("fraud_count"),
                avg("amount").alias("avg_fraud_amount"),
                avg("risk_score").alias("avg_risk_score")
            )

    def realtime_metrics(self, df):
        return df.groupBy(
            window(col("timestamp"), "1 minute")
        ).agg(
            count("*").alias("txn_count"),
            count(when(col("is_fraud") == True, 1)).alias("fraud_count"),
            avg("risk_score").alias("avg_risk"),
            avg(col("amount")).alias("avg_amount"),
            avg("processing_ms").alias("avg_latency_ms")
        )

    def start_alert_stream(self, threshold_risk: int = 80):
        raw = self.read_from_kafka("txn.raw")
        parsed = self.parse_stream(raw)
        high_risk = parsed.filter(col("risk_score") >= threshold_risk)

        query = high_risk.selectExpr("to_json(struct(*)) AS value") \
            .writeStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", KAFKA_BROKER) \
            .option("topic", "fraud.alerts.raw") \
            .option("checkpointLocation", "/tmp/spark-alert-checkpoint") \
            .trigger(processingTime="2 seconds") \
            .start()
        return query

    def start_dashboard_metrics(self):
        raw = self.read_from_kafka("txn.enriched")
        parsed = self.parse_stream(raw)
        metrics = self.realtime_metrics(parsed)

        query = metrics.writeStream \
            .outputMode("update") \
            .format("console") \
            .trigger(processingTime="10 seconds") \
            .start()
        return query

    def stop_all(self):
        self.spark.stop()
