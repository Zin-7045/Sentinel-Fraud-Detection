import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://frauduser:fraudpass@localhost:5432/frauddb")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "fraud_logs")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

KAFKA_RAW_TOPIC = "txn.raw"
KAFKA_ENRICHED_TOPIC = "txn.enriched"
KAFKA_ALERT_TOPIC = "fraud.alerts"
KAFKA_PREDICTIONS_TOPIC = "model.predictions"

RISK_THRESHOLD_HIGH = 80
RISK_THRESHOLD_MEDIUM = 60
RISK_THRESHOLD_LOW = 30

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "artifacts")
os.makedirs(MODEL_PATH, exist_ok=True)

FEATURE_COLUMNS = [
    "transaction_amount", "velocity_1h", "merchant_risk_score",
    "geo_anomaly_score", "device_fingerprint_match",
    "time_since_last_txn", "amount_vs_avg_30d", "channel_frequency_score",
    "hour_of_day", "day_of_week", "is_high_amount", "is_cross_border"
]
