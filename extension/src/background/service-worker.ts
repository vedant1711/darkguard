// ──────────────────────────────────────────────
// DarkGuard — Service Worker (MV3 background)
// Orchestrates signal collection, screenshot capture,
// API call, and result distribution.
// ──────────────────────────────────────────────

import type { CollectorPayload, AnalyzeRequest, Detection } from "../types/index";
import { captureScreenshot } from "../utils/screenshot";
import { analyzePageSignals } from "../utils/api-client";

/** Run the full analysis pipeline for the active tab. */
async function runAnalysis(tabId: number): Promise<void> {
    try {
        // 1. Collect signals from the content script
        const payload = await chrome.tabs.sendMessage(tabId, {
            type: "COLLECT_SIGNALS",
        }) as CollectorPayload;

        // 2. Capture a screenshot of the visible tab
        const screenshotB64 = await captureScreenshot();

        // 3. Build the API request (include all Phase 2 payload types)
        const request: AnalyzeRequest = {
            dom_metadata: payload.dom_metadata,
            text_content: payload.text_content,
            screenshot_b64: screenshotB64,
            review_text: payload.review_text,
            checkout_flow: payload.checkout_flow ?? null,
            nagging_events: payload.nagging_events ?? null,
            url: payload.dom_metadata.url,
        };

        // 4. Send to backend
        const response = await analyzePageSignals(request);
        const detections: Detection[] = response.detections;

        // 5. Store results for the popup
        await chrome.storage.local.set({
            lastDetections: detections,
            lastUrl: request.url,
            lastTimestamp: new Date().toISOString(),
        });

        // 6. Send detections to the content script for overlay rendering
        await chrome.tabs.sendMessage(tabId, {
            type: "DETECTIONS_READY",
            detections,
        });

        console.log(
            `[DarkGuard] Analysis complete: ${detections.length} detection(s) found.`
        );
    } catch (error) {
        console.error("[DarkGuard] Analysis failed:", error);

        // Store error state so popup can display it
        await chrome.storage.local.set({
            lastError: error instanceof Error ? error.message : String(error),
            lastTimestamp: new Date().toISOString(),
        });
    }
}

// ── Extension icon click → trigger analysis ──
chrome.action.onClicked.addListener(async (tab) => {
    if (!tab.id) return;

    // Inject content scripts if not already present
    try {
        await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ["content.js"],
        });
    } catch {
        // Script might already be injected — that's fine
    }

    await runAnalysis(tab.id);
});

// ── Message listener for popup or other contexts ──
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "TRIGGER_ANALYSIS") {
        chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
            const tab = tabs[0];
            if (tab?.id) {
                await runAnalysis(tab.id);
                sendResponse({ success: true });
            } else {
                sendResponse({ success: false, error: "No active tab" });
            }
        });
        return true; // keep channel open
    }
});
