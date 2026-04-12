"""
deep_scan/service.py — Playwright workflow execution engine.

Navigates through multi-step workflows on a website, analyzing each page
for dark patterns using the standard dispatcher pipeline. Takes annotated
screenshots at each step to provide visual proof of findings.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from playwright.async_api import async_playwright, Page, Browser, ElementHandle

from core.dispatcher import dispatch
from core.models import Detection
from core.regulatory_mapper import enrich_regulation_refs
from core.scoring import compute_score
from core.sanitizer import sanitize_payload
from crawler.service import _extract_dom_metadata, _extract_text_content, MAX_ELEMENTS
from deep_scan.annotator import annotate_screenshot
from deep_scan.workflows import (
    WORKFLOWS,
    WorkflowDefinition,
    WorkflowStep,
    PAYMENT_BLOCKLIST,
)

logger = logging.getLogger(__name__)

# Safety limits
MAX_STEPS_PER_WORKFLOW = 10
STEP_TIMEOUT_MS = 15_000
PAGE_SETTLE_MS = 2000


# ── Result dataclasses ───────────────────────────────────

@dataclass
class DeepScanStepResult:
    """Result of a single step in a deep scan workflow."""
    step_number: int
    page_url: str
    page_title: str
    action_taken: str
    screenshot_b64: str
    annotated_screenshot_b64: str
    detections: list[dict] = field(default_factory=list)
    patterns_found: int = 0
    timestamp: str = ""
    success: bool = True
    error: str = ""


@dataclass
class DeepScanWorkflowResult:
    """Result of one complete workflow execution."""
    workflow_id: str
    workflow_name: str
    workflow_description: str
    workflow_icon: str
    steps: list[DeepScanStepResult] = field(default_factory=list)
    total_patterns: int = 0
    categories_found: list[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class DeepScanResult:
    """Complete result of a deep scan across all workflows."""
    url: str
    workflows: list[DeepScanWorkflowResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    scan_id: int | None = None


# ── Engine ───────────────────────────────────────────────

def _is_payment_element(text: str) -> bool:
    """Check if element text matches the payment safety blocklist."""
    text_lower = text.strip().lower()
    return any(blocked in text_lower for blocked in PAYMENT_BLOCKLIST)


async def _try_find_element(page: Page, hints: list[str]) -> ElementHandle | None:
    """Try to find an element using a list of CSS/text hints."""
    for hint in hints:
        try:
            # Playwright text selector: button:has-text('Search')
            if ":has-text(" in hint:
                el = await page.query_selector(hint)
                if el and await el.is_visible():
                    return el
            else:
                el = await page.query_selector(hint)
                if el and await el.is_visible():
                    return el
        except Exception:
            continue
    return None


async def _analyze_page(page: Page, url: str) -> tuple[list[Detection], list[dict]]:
    """Run the full analysis pipeline on the current page.

    Returns:
        Tuple of (detections list, element_rects for annotation)
    """
    try:
        dom_metadata = await _extract_dom_metadata(page, url)
        text_content = await _extract_text_content(page)
    except Exception as e:
        logger.warning("Failed to extract page data: %s", e)
        return [], []

    # Build payload identical to what the extension/crawler sends
    payload: dict[str, object] = {
        "dom_metadata": dom_metadata,
        "text_content": text_content,
        "screenshot_b64": "",
        "review_text": None,
        "checkout_flow": None,
        "nagging_events": None,
        "url": url,
    }
    payload = sanitize_payload(payload)

    detections = await dispatch(payload)
    detections = enrich_regulation_refs(detections)

    # Ensure all detected elements have a bounding rect for annotations
    selectors = list({d.element_selector for d in detections if d.element_selector and d.element_selector != "body"})
    
    # Extract authentic bounding rects dynamically
    element_rects: dict[str, dict] = {}
    if selectors:
        try:
            element_rects = await page.evaluate("""(selectors) => {
                const rects = {};
                for (const sel of selectors) {
                    try {
                        const el = document.querySelector(sel);
                        if (el) {
                            const r = el.getBoundingClientRect();
                            rects[sel] = { x: r.x, y: r.y, width: r.width, height: r.height };
                        }
                    } catch(e) {}
                }
                return rects;
            }""", selectors)
        except Exception as e:
            logger.warning("Failed to extract dynamic bounding rects: %s", e)

    # Attach bounding rects to detections for annotation
    det_dicts: list[dict] = []
    for d in detections:
        dd = asdict(d)
        dd["bounding_rect"] = element_rects.get(d.element_selector)
        det_dicts.append(dd)

    return detections, det_dicts


async def _execute_step(
    page: Page,
    step: WorkflowStep,
    step_number: int,
    url: str,
) -> DeepScanStepResult:
    """Execute a single workflow step and analyze the resulting page."""

    action_taken = step.intent
    success = True
    error_msg = ""

    try:
        if step.action == "navigate":
            await page.goto(url, wait_until="networkidle", timeout=STEP_TIMEOUT_MS)
            action_taken = f"Navigated to {url}"

        elif step.action == "find_and_click":
            success = False
            for attempt in range(5):
                el = await _try_find_element(page, step.hints)
                if not el:
                    await page.wait_for_timeout(2000)
                    continue

                # Safety check: don't click payment buttons
                el_text = await el.text_content() or ""
                if _is_payment_element(el_text):
                    action_taken = f"Found '{el_text.strip()[:40]}' but skipped (payment safety)"
                    success = True
                    break
                
                try:
                    await el.scroll_into_view_if_needed()
                    await el.click(timeout=5000)
                    
                    # Try waiting for network idle gracefully
                    try:
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    
                    # Provide an extra moment for SPAs
                    await page.wait_for_timeout(PAGE_SETTLE_MS)
                    
                    action_taken = f"Clicked: '{el_text.strip()[:60]}'"
                    success = True
                    break
                except Exception as e:
                    # Click might have failed (e.g. element intercepted)
                    if attempt == 4:
                        error_msg = f"Failed to click element: {str(e)[:200]}"
                        action_taken = f"Found but couldn't click: {step.intent}"
                    else:
                        await page.wait_for_timeout(2000)

            if not success and not error_msg:
                action_taken = f"Could not find element for: {step.intent}"
                error_msg = "Element not found with any hint selector after 5 retries (10s total)"

        elif step.action == "analyze_banner":
            action_taken = "Analyzing cookie/consent banner"

        elif step.action == "analyze_only":
            action_taken = step.intent

        # Wait for page to settle
        await page.wait_for_timeout(PAGE_SETTLE_MS)

    except Exception as e:
        logger.warning("Step %d failed: %s", step_number, e)
        action_taken = f"Failed: {step.intent}"
        success = False
        error_msg = str(e)[:200]

    # Take screenshot
    try:
        screenshot_bytes = await page.screenshot(full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    except Exception:
        screenshot_b64 = ""

    # Run analysis on current page state
    current_url = page.url
    current_title = await page.title()
    detections, det_dicts = await _analyze_page(page, current_url)

    # Annotate screenshot
    annotated = annotate_screenshot(screenshot_b64, det_dicts)

    # Strip bounding_rect from det_dicts before returning (not needed in API response)
    for dd in det_dicts:
        dd.pop("bounding_rect", None)

    return DeepScanStepResult(
        step_number=step_number,
        page_url=current_url,
        page_title=current_title,
        action_taken=action_taken,
        screenshot_b64=screenshot_b64,
        annotated_screenshot_b64=annotated,
        detections=det_dicts,
        patterns_found=len(detections),
        timestamp=datetime.now(timezone.utc).isoformat(),
        success=success,
        error=error_msg,
    )


async def _execute_workflow(
    browser: Browser,
    workflow_id: str,
    workflow: WorkflowDefinition,
    url: str,
) -> DeepScanWorkflowResult:
    """Execute a single workflow from start to finish."""
    result = DeepScanWorkflowResult(
        workflow_id=workflow_id,
        workflow_name=workflow.name,
        workflow_description=workflow.description,
        workflow_icon=workflow.icon,
    )

    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    page = await context.new_page()

    all_categories: set[str] = set()
    total_patterns = 0

    try:
        for i, step in enumerate(workflow.steps[:MAX_STEPS_PER_WORKFLOW]):
            step_result = await _execute_step(page, step, i + 1, url)
            result.steps.append(step_result)
            total_patterns += step_result.patterns_found

            for det in step_result.detections:
                all_categories.add(det.get("category", ""))

            # Abort workflow to prevent repeating steps on same page if a step failed
            if not step_result.success:
                logger.info("Workflow '%s' aborted at step %d due to failure.", workflow_id, i + 1)
                break

    except Exception as e:
        logger.exception("Workflow '%s' failed: %s", workflow_id, e)
    finally:
        await context.close()

    result.total_patterns = total_patterns
    result.categories_found = sorted(all_categories - {""})
    result.completed = True

    return result


async def run_deep_scan(
    url: str,
    workflow_ids: list[str] | None = None,
) -> DeepScanResult:
    """Run a deep scan on a URL with the specified workflows.

    Args:
        url: The base URL to scan.
        workflow_ids: List of workflow IDs to run. If None, runs all workflows.

    Returns:
        DeepScanResult with all workflow results.
    """
    if workflow_ids is None:
        workflow_ids = list(WORKFLOWS.keys())

    # Filter to valid workflow IDs
    selected = [
        (wid, WORKFLOWS[wid])
        for wid in workflow_ids
        if wid in WORKFLOWS
    ]

    if not selected:
        return DeepScanResult(url=url, summary={"error": "No valid workflows selected"})

    result = DeepScanResult(url=url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for wid, workflow in selected:
                logger.info("Starting workflow '%s' on %s", wid, url)
                wf_result = await _execute_workflow(browser, wid, workflow, url)
                result.workflows.append(wf_result)
                logger.info(
                    "Workflow '%s' complete: %d patterns across %d steps",
                    wid, wf_result.total_patterns, len(wf_result.steps),
                )
        finally:
            await browser.close()

    # Build summary
    total_patterns = sum(w.total_patterns for w in result.workflows)
    all_categories = set()
    for w in result.workflows:
        all_categories.update(w.categories_found)

    result.summary = {
        "total_patterns": total_patterns,
        "total_steps": sum(len(w.steps) for w in result.workflows),
        "workflows_completed": sum(1 for w in result.workflows if w.completed),
        "workflows_total": len(selected),
        "categories_found": sorted(all_categories),
    }

    return result


def run_deep_scan_sync(
    url: str,
    workflow_ids: list[str] | None = None,
) -> DeepScanResult:
    """Synchronous wrapper for run_deep_scan."""
    return asyncio.run(run_deep_scan(url, workflow_ids))
