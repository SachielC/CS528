import time
import requests
from datetime import datetime

LB_URL = "http://34.31.254.131:8080/"

def main():
    i = 1

    while True:
        try:
            print(f"\nRequest #{i} - {datetime.utcnow().isoformat()}")

            response = requests.get(LB_URL, timeout=5)

            print("Status Code:", response.status_code)

            # Print headers
            zone = response.headers.get("X-Zone", "N/A")
            print("X-Zone:", zone)

            # Print body
            print("Body:", response.text.strip())

        except Exception as e:
            print("ERROR:", str(e))

        i += 1
        time.sleep(.1)


if __name__ == "__main__":
    main()