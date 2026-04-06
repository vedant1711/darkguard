import requests
import json
import time

url = "http://127.0.0.1:8000/api/scans/crawl"
payload = {
    "url": "https://www.booking.com/"
}

print(f"Testing {payload['url']} via Crawl API...")
start = time.time()
try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}")
    print(f"Time Taken: {time.time() - start:.2f} seconds")
    
    data = response.json()
    with open('output_results.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Saved output to output_results.json")
except Exception as e:
    print(f"Error occurred: {e}")
