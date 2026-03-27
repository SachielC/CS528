import os
import json
import logging
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from google.cloud import storage, pubsub_v1
import pymysql
from pymysql.cursors import DictCursor

BUCKET_NAME = os.environ["BUCKET_NAME"]
PROJECT_ID = os.environ["GCP_PROJECT"]
TOPIC_NAME = os.environ["TOPIC_NAME"]

# Cloud SQL / MySQL
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")  
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ["DB_USER"]
DB_PASS = os.environ["DB_PASS"]
DB_NAME = os.environ["DB_NAME"]

FORBIDDEN = {
    "North Korea", "Iran", "Cuba", "Myanmar",
    "Syria", "Iraq", "Libya", "Zimbabwe", "Sudan"
}

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=DictCursor,
        autocommit=True
    )

def get_time_of_day():
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 18:
        return "afternoon"
    return "evening"

def extract_request_info(handler):
    start = time.perf_counter()
    headers = handler.headers

    try:
        age = int(headers.get("X-age", 0))
    except ValueError:
        age = 0

    try:
        income = int(headers.get("X-income", 0))
    except ValueError:
        income = 0

    data = {
        "country": headers.get("X-country", "").strip(),
        "gender": headers.get("X-gender", "").strip(),
        "age": age,
        "income": income,
        "client_ip": handler.client_address[0],
        "requested_file": handler.path,
        "time_of_day": datetime.now()
    }

    logging.info(f"[Timing] Header extraction: {time.perf_counter() - start:.6f}s")
    return data

def insert_request(data, is_banned):
    conn = None
    request_id = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO requests
                (country, client_ip, gender, age, income, is_banned, time_of_day, requested_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data["country"], data["client_ip"], data["gender"],
                data["age"], data["income"], is_banned,
                data["time_of_day"], data["requested_file"]
            ))
            request_id = cursor.lastrowid  
    except Exception as e:
        logging.error(f"DB insert_request failed: {e}")
    finally:
        if conn:
            conn.close()
    return request_id

def insert_failed_request(path, error_code, request_id=None):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO failed_requests
                (time_of_request, requested_file, error_code, request_id)
                VALUES (NOW(), %s, %s, %s)
            """, (path, error_code, request_id))
    except Exception as e:
        logging.error(f"DB insert_failed_request failed: {e}")
    finally:
        if conn:
            conn.close()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    request_queue_size = 100

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        total_start = time.perf_counter()
        data = extract_request_info(self)
        path = self.path
        country = data["country"]

        if country in FORBIDDEN:
            try:
                publisher.publish(
                    topic_path,
                    json.dumps({
                        "country": country,
                        "path": path,
                        "timestamp": datetime.utcnow().isoformat()
                    }).encode()
                )
            except Exception as e:
                logging.error(f"Pub/Sub publish failed: {e}")

            req_id = insert_request(data, True)
            insert_failed_request(path, 400, request_id=req_id)

            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Forbidden Country")
            logging.info(f"[Timing] 400 processed in {time.perf_counter() - total_start:.6f}s")
            return

        try:
            file_start = time.perf_counter()
            blob = bucket.blob(path.lstrip("/"))

            if not blob.exists():
                req_id = insert_request(data, False)
                insert_failed_request(path, 404, request_id=req_id)

                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"404 Not Found")
                logging.info(f"[Timing] 404 processed in {time.perf_counter() - total_start:.6f}s")
                return

            content = blob.download_as_bytes()
            logging.info(f"[Timing] File read: {time.perf_counter() - file_start:.6f}s")

        except Exception as e:
            logging.error(f"Storage error: {e}")
            req_id = insert_request(data, False)
            insert_failed_request(path, 500, request_id=req_id)

            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Storage Error")
            return

        send_start = time.perf_counter()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(content)
        logging.info(f"[Timing] Response send: {time.perf_counter() - send_start:.6f}s")

        insert_request(data, False)
        logging.info(f"[Timing] TOTAL request time: {time.perf_counter() - total_start:.6f}s")

    def _fail(self, code):
        data = extract_request_info(self)
        req_id = insert_request(data, False)
        insert_failed_request(self.path, code, request_id=req_id)

        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Implemented")

    def do_POST(self): self._fail(501)
    def do_PUT(self): self._fail(501)
    def do_DELETE(self): self._fail(501)
    def do_PATCH(self): self._fail(501)
    def do_OPTIONS(self): self._fail(501)
    def do_CONNECT(self): self._fail(501)
    def do_TRACE(self): self._fail(501)

#  MAIN 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = ThreadedHTTPServer(("0.0.0.0", 8080), MyHandler)
    print("Server running on port 8080")
    server.serve_forever()
