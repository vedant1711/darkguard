"""Quick test: Deep scan a website via the API."""
import json
import time
import requests

URL = "https://www.booking.com/"
API = "http://localhost:8001/api/scans/deep-scan"

print(f"Deep scanning {URL}...")
print("Workflows: consent_privacy, signup_flow")
print("This may take 30-120 seconds...\n")

start = time.time()
resp = requests.post(API, json={
    "url": URL,
    "workflows": ["consent_privacy", "signup_flow"],
}, timeout=300)  # 5 minute timeout for deep scan
elapsed = time.time() - start

print(f"Status: {resp.status_code}")
print(f"Time: {elapsed:.1f}s\n")

if resp.status_code == 200:
    data = resp.json()
    summary = data.get("summary", {})
    print(f"=== SUMMARY ===")
    print(f"Total patterns: {summary.get('total_patterns', 0)}")
    print(f"Total steps: {summary.get('total_steps', 0)}")
    print(f"Workflows completed: {summary.get('workflows_completed', 0)}/{summary.get('workflows_total', 0)}")
    print(f"Categories found: {summary.get('categories_found', [])}")
    print()
    
    for wf in data.get("workflows", []):
        print(f"--- {wf['workflow_icon']} {wf['workflow_name']} ---")
        print(f"    Steps: {len(wf['steps'])}, Patterns: {wf['total_patterns']}")
        for step in wf["steps"]:
            has_screenshot = "Yes" if step.get("annotated_screenshot_b64") and len(step.get("annotated_screenshot_b64", "")) > 100 else "No"
            print(f"    Step {step['step_number']}: {step['action_taken']}")
            print(f"      URL: {step['page_url'][:80]}")
            print(f"      Patterns: {step['patterns_found']}, Screenshot: {has_screenshot}")
            if step["detections"]:
                for det in step["detections"][:3]:
                    print(f"        → [{det['category']}] {det['explanation'][:100]}")
        print()

    print("Full results saved to deep_scan_results.json")
    # Save truncated result
    clean = json.loads(json.dumps(data))
    for wf in clean.get("workflows", []):
        for step in wf["steps"]:
            if step.get("screenshot_b64"):
                step["screenshot_b64"] = f"<{len(step['screenshot_b64'])} chars>"
            if step.get("annotated_screenshot_b64"):
                step["annotated_screenshot_b64"] = f"<{len(step['annotated_screenshot_b64'])} chars>"
    with open("deep_scan_results.json", "w") as f:
        json.dump(clean, f, indent=2)
else:
    print(f"Error: {resp.text[:500]}")
