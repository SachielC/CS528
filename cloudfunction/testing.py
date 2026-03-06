import requests

BASE_URL = "https://recieve-x7635okvpq-uc.a.run.app"

tests = [
    {
        "description": "Valid GET request (query param)",
        "url": f"{BASE_URL}?file=2.html",
        "method": "GET",
        "headers": {"X-country": "USA"},
        "expected": 200
    },
    {
        "description": "Valid GET request (path style)",
        "url": f"{BASE_URL}/webdir/2.html",
        "method": "GET",
        "headers": {"X-country": "USA"},
        "expected": 200
    },
    {
        "description": "GET request for non-existent file",
        "url": f"{BASE_URL}?file=99999.html",
        "method": "GET",
        "headers": {"X-country": "USA"},
        "expected": 404
    },
    {
        "description": "GET request from forbidden country (should publish to Pub/Sub)",
        "url": f"{BASE_URL}?file=2.html",
        "method": "GET",
        "headers": {"X-country": "North Korea"},
        "expected": 400
    },
    {
        "description": "POST request to check 501",
        "url": f"{BASE_URL}?file=2.html",
        "method": "POST",
        "headers": {"X-country": "USA"},
        "expected": 501
    },
    {
        "description": "GET request from forbidden country (test Iran) to trigger Pub/Sub",
        "url": f"{BASE_URL}?file=2.html",
        "method": "GET",
        "headers": {"X-country": "Iran"},
        "expected": 400
    }
]

for test in tests:
    method = test["method"].upper()
    headers = test["headers"]

    try:
        if method == "GET":
            r = requests.get(test["url"], headers=headers)
        elif method == "POST":
            r = requests.post(test["url"], headers=headers)
        else:
            print(f"Unsupported method: {method}")
            continue

        print(f"\nTest: {test['description']}")
        print(f"URL: {test['url']}")
        print(f"Expected status: {test['expected']}, Actual status: {r.status_code}")
        print(f"Response body:\n{r.text}")

    except Exception as e:
        print(f"\nTest: {test['description']} FAILED with exception: {e}")
        from google.cloud import pubsub_v1