from google.cloud import pubsub_v1, storage
import json
from datetime import datetime
import time


# Configuration

PROJECT_ID = "coral-mission-485618-m4"
SUBSCRIPTION_NAME = "forbidden-sub"
TOPIC_NAME = "forbidden-topic"
BUCKET_NAME = "hw2bucketmanyrank"
LOG_PATH = "forbidden_logs/log.txt"


subscriber = pubsub_v1.SubscriberClient()
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

try:
    subscriber.create_subscription(
        name=subscription_path,
        topic=subscriber.topic_path(PROJECT_ID, TOPIC_NAME)
    )
except Exception:
    pass  

def callback(message):
    try:
        data = json.loads(message.data.decode("utf-8"))

        log_entry = f"{datetime.utcnow().isoformat()} - FORBIDDEN: {data}\n"

        print(log_entry)

        blob = bucket.blob(LOG_PATH)
        existing = ""
        if blob.exists():
            existing = blob.download_as_text()
        blob.upload_from_string(existing + log_entry)

        # Acknowledge message
        message.ack()

    except Exception as e:
        print("Error handling message:", e)
        message.nack()


streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

print(f"Listening for forbidden messages on {TOPIC_NAME}...")

try:
 
    streaming_pull_future.result()
except KeyboardInterrupt:
   
    streaming_pull_future.cancel()
