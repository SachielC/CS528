import os
import json
import logging
import requests

from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from google.cloud import storage, pubsub_v1


# ---------------- CONFIG ----------------
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
    daemon_threads = True
    request_queue_size = 10


class MyHandler(BaseHTTPRequestHandler):
    
    # | | | |                      | | | |
    # V V V V NEW FUNCTION FOR HW8 V V V V
    def get_zone(self):
        try:
            r = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/zone",
                headers={"Metadata-Flavor": "Google"},
                timeout=2
            )
            return r.text.split("/")[-1]
        except Exception as e:
            logging.warning(f"Zone fetch failed: {e}")
            return "unknown"

    def do_GET(self):
        zone = self.get_zone()

        try:
            if self.path == "/" or self.path == "":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("X-Zone", zone)
                self.end_headers()
                self.wfile.write(b"OK")
                return

            blob_path = self.path.lstrip("/")

            country = self.headers.get("X-country", "")
            if country in FORBIDDEN:
                msg = {
                    "country": country,
                    "path": self.path,
                    "timestamp": datetime.utcnow().isoformat()
                }
                publisher.publish(topic_path, json.dumps(msg).encode())
                logging.warning(f"403: {msg}")

                self.send_response(403)
                self.send_header("Content-Type", "text/plain")
                self.send_header("X-Zone", zone)
                self.end_headers()
                self.wfile.write(b"Permission Denied")
                return

            blob = bucket.blob(blob_path)

            if not blob.exists():
                logging.warning(f"404: {blob_path}")

                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.send_header("X-Zone", zone)
                self.end_headers()
                self.wfile.write(b"404 Not Found")
                return

            content = blob.download_as_bytes()

            logging.info(f"200: {blob_path}")

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("X-Zone", zone)
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            logging.error(f"Server error: {e}")

            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("X-Zone", zone)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

    def do_POST(self): self.not_implemented()
    def do_PUT(self): self.not_implemented()
    def do_DELETE(self): self.not_implemented()
    def do_PATCH(self): self.not_implemented()
    def do_OPTIONS(self): self.not_implemented()
    def do_CONNECT(self): self.not_implemented()
    def do_TRACE(self): self.not_implemented()
    def do_HEAD(self): self.not_implemented()

    def not_implemented(self):
        zone = self.get_zone()
        logging.warning(f"501: {self.command}")

        self.send_response(501)
        self.send_header("Content-Type", "text/plain")
        self.send_header("X-Zone", zone)
        self.end_headers()
        self.wfile.write(b"501 Not Implemented")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    server = ThreadedHTTPServer(("", 8080), MyHandler)
    print("Server running on port 8080")

    server.serve_forever()
