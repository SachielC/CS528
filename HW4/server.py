from flask import Request
from google.cloud import storage, pubsub_v1
import os
import json
from datetime import datetime


BUCKET_NAME = os.environ.get("BUCKET_NAME")
PROJECT_ID = os.environ.get("GCP_PROJECT")
TOPIC_NAME = os.environ.get("TOPIC_NAME")


FORBIDDEN = [
    "North Korea", "Iran", "Cuba", "Myanmar",
    "Syria", "Iraq", "Libya", "Zimbabwe", "Sudan"
]

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)


def log_event(event_type, details):
    entry = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details
    }
    print(json.dumps(entry))


def recieve(request: Request):
    try:
        log_event("request_received", {
            "method": request.method,
            "path": request.path,
            "args": dict(request.args)
        })

 
        if request.method != "GET":
            log_event("501_error", {
                "method": request.method
            })
            return ("501 Not Implemented", 501)

        country = request.headers.get("X-country", "")

        if country in FORBIDDEN:
            message = {
                "country": country,
                "path": request.path,
                "method": request.method,
                "timestamp": datetime.utcnow().isoformat()
            }

            publisher.publish(
                topic_path,
                json.dumps(message).encode("utf-8")
            )

            log_event("forbidden_country", message)

            return ("Permission Denied", 400)


        blob_path = None

        # Case A: URL path like /webdir/123.html
        if request.path and request.path != "/":
            blob_path = request.path.lstrip("/")

        else:
            filename = request.args.get("file")
            if not filename:
                return ("No file specified", 400)

            blob_path = f"webdir/{filename}"


        blob = bucket.blob(blob_path)

        if not blob.exists():
            log_event("404_error", {
                "file": blob_path
            })
            return (f"404 Not Found: {blob_path}", 404)

        content = blob.download_as_text()

        log_event("200_success", {
            "file": blob_path
        })

        return (content, 200)

    except Exception as e:
        log_event("500_error", {
            "error": str(e)
        })
        return ("Internal Server Error", 500)