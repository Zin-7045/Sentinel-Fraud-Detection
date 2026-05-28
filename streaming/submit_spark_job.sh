#!/bin/bash
# Submit the Spark Structured Streaming job to the Sentinel Spark cluster
# Usage: docker compose exec spark-submit bash /opt/streaming/submit_spark_job.sh

# Install Python deps inside the container (needed for spark-submit Python jobs)
pip install -q kafka-python pandas numpy 2>/dev/null

# Submit the PySpark streaming job
spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
  --deploy-mode client \
  /opt/streaming/spark_job.py
