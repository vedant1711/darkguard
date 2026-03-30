// ──────────────────────────────────────────────
// DarkGuard — Overlay Renderer
// Injects shadow-DOM overlays on flagged elements.
// ──────────────────────────────────────────────

import type { Detection } from "../types/index";

/** Colour map by severity. */
const SEVERITY_COLORS: Record<string, string> = {
    high: "rgba(220, 38, 38, 0.6)",    // red
    medium: "rgba(245, 158, 11, 0.55)", // amber
    low: "rgba(59, 130, 246, 0.5)",     // blue
};

/** Human-readable category labels. */
const CATEGORY_LABELS: Record<string, string> = {
    // Phase 1
    urgency_scarcity: "Urgency / Scarcity",
    confirmshaming: "Confirmshaming",
    visual_interference: "Visual Interference",
    preselection: "Preselection",
    hidden_costs: "Hidden Costs",
    misdirection: "Misdirection",
    fake_social_proof: "Fake Social Proof",
    // Phase 2
    asymmetric_choice: "Asymmetric Choice",
    prechecked_consent: "Pre-checked Consent",
    basket_sneaking: "Basket Sneaking",
    drip_pricing: "Drip Pricing",
    roach_motel: "Roach Motel",
    forced_continuity: "Forced Continuity",
    plan_comparison_trick: "Plan Comparison Trick",
    privacy_zuckering: "Privacy Zuckering",
    notification_inflation: "Notification Inflation",
    persistent_nagging: "Persistent Nagging",
    price_anchoring: "Price Anchoring",
    bnpl_deception: "BNPL Deception",
    intermediate_currency: "Intermediate Currency",
};

const OVERLAY_ATTR = "data-darkguard-overlay";

/** Remove all existing overlays from the page. */
export function clearOverlays(): void {
    const existing = document.querySelectorAll(`[${OVERLAY_ATTR}]`);
    existing.forEach((el) => el.remove());
}

/** Render detection overlays on the page. */
export function renderOverlays(detections: Detection[]): void {
    clearOverlays();

    for (const det of detections) {
        const target = document.querySelector(det.element_selector);
        if (!target) continue;

        const rect = target.getBoundingClientRect();

        // Create container with Shadow DOM to isolate styles
        const container = document.createElement("div");
        container.setAttribute(OVERLAY_ATTR, "true");
        container.style.cssText = `
      position: fixed;
      left: ${rect.left}px;
      top: ${rect.top}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      pointer-events: none;
      z-index: 2147483647;
    `;

        const shadow = container.attachShadow({ mode: "closed" });

        const borderColor = SEVERITY_COLORS[det.severity] ?? SEVERITY_COLORS["low"];
        const corroboratedBadge = det.corroborated
            ? '<span class="badge corr">⚠ Corroborated</span>'
            : "";

        const categoryLabel =
            CATEGORY_LABELS[det.category] ??
            det.category.replace(/_/g, " ");

        // Regulation refs badge
        const refsHtml =
            det.regulation_refs && det.regulation_refs.length > 0
                ? `<div class="refs">${det.regulation_refs.map((r) => `<span class="ref-badge">${r}</span>`).join(" ")}</div>`
                : "";

        // Analyzer source badge
        const analyzerBadge = det.analyzer_name
            ? `<span class="badge source">${det.analyzer_name}</span>`
            : "";

        shadow.innerHTML = `
      <style>
        :host {
          all: initial;
        }
        .overlay-border {
          position: absolute;
          inset: 0;
          border: 3px solid ${borderColor};
          border-radius: 4px;
          pointer-events: none;
          box-sizing: border-box;
        }
        .tooltip {
          position: absolute;
          bottom: calc(100% + 6px);
          left: 0;
          background: #1e1e2e;
          color: #cdd6f4;
          font: 13px/1.4 'Segoe UI', system-ui, sans-serif;
          padding: 8px 12px;
          border-radius: 8px;
          max-width: 360px;
          pointer-events: auto;
          opacity: 0;
          transition: opacity 0.15s ease;
          box-shadow: 0 4px 16px rgba(0,0,0,0.4);
          z-index: 2147483647;
        }
        .overlay-border:hover ~ .tooltip,
        .tooltip:hover {
          opacity: 1;
        }
        .category {
          font-weight: 600;
          color: #f38ba8;
          margin-bottom: 4px;
        }
        .explanation {
          font-size: 12px;
          color: #a6adc8;
        }
        .confidence {
          font-size: 11px;
          color: #6c7086;
          margin-top: 4px;
        }
        .badge {
          display: inline-block;
          font-size: 10px;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
          margin-left: 6px;
          vertical-align: middle;
        }
        .badge.corr {
          background: #f38ba8;
          color: #1e1e2e;
        }
        .badge.source {
          background: #89b4fa;
          color: #1e1e2e;
        }
        .refs {
          margin-top: 4px;
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }
        .ref-badge {
          display: inline-block;
          font-size: 9px;
          font-weight: 600;
          padding: 1px 5px;
          border-radius: 3px;
          background: #313244;
          color: #a6e3a1;
        }
      </style>
      <div class="overlay-border" style="pointer-events: auto; cursor: help;"></div>
      <div class="tooltip">
        <div class="category">
          ${categoryLabel}${corroboratedBadge}${analyzerBadge}
        </div>
        <div class="explanation">${det.explanation}</div>
        <div class="confidence">Confidence: ${Math.round(det.confidence * 100)}% · ${det.severity}</div>
        ${refsHtml}
      </div>
    `;

        document.body.appendChild(container);
    }
}

// ── Listen for detection results from the service worker ──
chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "DETECTIONS_READY") {
        renderOverlays(message.detections as Detection[]);
    }
});
