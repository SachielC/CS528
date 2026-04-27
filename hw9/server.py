import os
import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from google.cloud import storage, pubsub_v1

BUCKET_NAME = os.environ["BUCKET_NAME"]
PROJECT_ID = os.environ["GCP_PROJECT"]
TOPIC_NAME = os.environ["TOPIC_NAME"]

FORBIDDEN = [
    "North Korea", "Iran", "Cuba", "Myanmar",
    "Syria", "Iraq", "Libya", "Zimbabwe", "Sudan"
]

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    request_queue_size = 5


class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        country = self.headers.get("X-country", "")

        # ---------------- FORBIDDEN CASE ----------------
        if country in FORBIDDEN:
            msg = {
                "country": country,
                "path": self.path,
                "timestamp": datetime.utcnow().isoformat()
            }

            data = json.dumps(msg).encode("utf-8")

            # 🔥 IMPORTANT FIX: FORCE PUBLISH CONFIRMATION
            future = publisher.publish(topic_path, data)
            message_id = future.result()   # blocks until published

            logging.critical(f"FORBIDDEN REQUEST PUBLISHED: {msg}")
            logging.critical(f"PUBSUB MESSAGE ID: {message_id}")

            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Permission Denied")
            return

        # ---------------- FILE SERVING ----------------
        blob_path = self.path.lstrip("/")
        blob = bucket.blob(blob_path)

        if not blob.exists():
            logging.warning(f"404: {blob_path}")
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        content = blob.download_as_bytes()
        logging.info(f"200: {blob_path}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(content)

    # ---------------- NOT IMPLEMENTED METHODS ----------------
    def do_POST(self): self.not_implemented()
    def do_PUT(self): self.not_implemented()
    def do_DELETE(self): self.not_implemented()
    def do_PATCH(self): self.not_implemented()
    def do_OPTIONS(self): self.not_implemented()
    def do_CONNECT(self): self.not_implemented()
    def do_TRACE(self): self.not_implemented()
    def do_HEAD(self): self.not_implemented()

    def not_implemented(self):
        logging.warning(f"501: {self.command}")
        self.send_response(501)
        self.end_headers()
        self.wfile.write(b"501 Not Implemented")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = ThreadedHTTPServer(("", 8080), MyHandler)
    print("Server running on port 8080")
    server.serve_forever()