import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.pipeline.data_ingestion import TransactionProducer
from backend.pipeline.kafka_pipeline import KafkaClient

producer = TransactionProducer(seed=42)
client = KafkaClient()

print("[KafkaProducer] Streaming transactions to Kafka...")
count = 0
try:
    while True:
        txn = producer.generate()
        client.send("txn.raw", value=txn, key=txn.get("user_id"))
        count += 1
        if txn.get("is_fraud"):
            print(f"  ⚠ [#{count}] FRAUD: {txn['transaction_id']} | ${txn['amount']} | {txn['fraud_type']}")
        if count % 100 == 0:
            print(f"  ✓ [{count}] transactions published")
        time.sleep(0.02)
except KeyboardInterrupt:
    print(f"\n[KafkaProducer] Stopped. Published {count} transactions.")
    client.close()
