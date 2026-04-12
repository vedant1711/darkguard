"""Direct test: Run deep scan without Django."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
os.environ["DJANGO_SETTINGS_MODULE"] = "darkguard.settings"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import django
django.setup()

import asyncio
import time
import json

from deep_scan.service import run_deep_scan

async def main():
    url = "https://www.booking.com/"
    print(f"Deep scanning {url}...")
    print("Workflows: consent_privacy\n")
    
    start = time.time()
    result = await run_deep_scan(url, ["consent_privacy"])
    elapsed = time.time() - start
    
    print(f"Time: {elapsed:.1f}s\n")
    print(f"=== SUMMARY ===")
    print(f"Total patterns: {result.summary.get('total_patterns', 0)}")
    print(f"Total steps: {result.summary.get('total_steps', 0)}")
    print(f"Categories found: {result.summary.get('categories_found', [])}")
    print()
    
    for wf in result.workflows:
        print(f"--- {wf.workflow_icon} {wf.workflow_name} ---")
        for step in wf.steps:
            ss = "Yes" if step.annotated_screenshot_b64 and len(step.annotated_screenshot_b64) > 100 else "No"
            print(f"  Step {step.step_number}: {step.action_taken}")
            print(f"    URL: {step.page_url[:80]}")
            print(f"    Patterns: {step.patterns_found}, Screenshot: {ss}, Success: {step.success}")
            if step.detections:
                for det in step.detections[:3]:
                    print(f"      → [{det['category']}] {det['explanation'][:100]}")

asyncio.run(main())
