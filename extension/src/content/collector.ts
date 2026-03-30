// ──────────────────────────────────────────────
// DarkGuard — DOM / Text / Flow Collector
// Scrapes DOM metadata, visible text, checkout flow data,
// and nagging events from the active page.
// ──────────────────────────────────────────────

import type {
    CollectorPayload,
    DomMetadata,
    TextContent,
    ElementInfo,
    BoundingRect,
    ComputedStyleInfo,
    LabeledElement,
    CheckoutFlowData,
    CheckoutItem,
    NaggingEventsData,
    NaggingEvent,
} from "../types/index";
import {
    sanitizeDomMetadata,
    sanitizeTextContent,
    sanitizeReviewText,
    sanitizeCheckoutFlow,
    sanitizeNaggingEvents,
} from "./sanitizer";

/** Maximum body text length to send to the backend. */
const MAX_BODY_TEXT_LENGTH = 5000;

// ── Nagging event tracker (runs persistently) ────────────
const _naggingEvents: NaggingEvent[] = [];
let _hasPersistentOverlay = false;

/** Build a unique CSS selector for an element. */
function buildSelector(el: Element): string {
    if (el.id) return `#${CSS.escape(el.id)}`;

    const parts: string[] = [];
    let current: Element | null = el;

    while (current && current !== document.documentElement) {
        let selector = current.tagName.toLowerCase();
        if (current.id) {
            selector = `#${CSS.escape(current.id)}`;
            parts.unshift(selector);
            break;
        }

        const parent: Element | null = current.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children).filter(
                (c: Element) => c.tagName === current!.tagName
            );
            if (siblings.length > 1) {
                const index = siblings.indexOf(current) + 1;
                selector += `:nth-of-type(${index})`;
            }
        }
        parts.unshift(selector);
        current = parent;
    }

    return parts.join(" > ");
}

function getBoundingRect(el: Element): BoundingRect {
    const rect = el.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
}

function getComputedStyleInfo(el: Element): ComputedStyleInfo {
    const styles = window.getComputedStyle(el);
    return {
        color: styles.color,
        background_color: styles.backgroundColor,
        font_size: styles.fontSize,
        opacity: styles.opacity,
        display: styles.display,
        visibility: styles.visibility,
    };
}

function toElementInfo(el: Element): ElementInfo {
    const attrs: Record<string, string> = {};
    for (const attr of Array.from(el.attributes)) {
        attrs[attr.name] = attr.value;
    }
    return {
        selector: buildSelector(el),
        tag_name: el.tagName.toLowerCase(),
        text_content: (el.textContent ?? "").trim().slice(0, 200),
        attributes: attrs,
        bounding_rect: getBoundingRect(el),
        computed_styles: getComputedStyleInfo(el),
    };
}

/** Collect hidden elements (display:none, visibility:hidden, opacity:0). */
function collectHiddenElements(): ElementInfo[] {
    const results: ElementInfo[] = [];
    const all = document.querySelectorAll("*");

    for (const el of all) {
        const styles = window.getComputedStyle(el);
        if (
            styles.display === "none" ||
            styles.visibility === "hidden" ||
            styles.opacity === "0"
        ) {
            results.push(toElementInfo(el));
            if (results.length >= 50) break; // cap to avoid huge payloads
        }
    }
    return results;
}

/** Collect interactive elements (buttons, links, inputs). */
function collectInteractiveElements(): ElementInfo[] {
    const selectors =
        'button, [role="button"], a[href], input[type="submit"], input[type="button"], select';
    const elements = document.querySelectorAll(selectors);
    return Array.from(elements).slice(0, 100).map(toElementInfo);
}

/** Collect pre-checked checkboxes and radio buttons. */
function collectPrecheckedInputs(): ElementInfo[] {
    const inputs = document.querySelectorAll<HTMLInputElement>(
        'input[type="checkbox"]:checked, input[type="radio"]:checked'
    );
    return Array.from(inputs).map(toElementInfo);
}

/** Collect button / CTA labels. */
function collectButtonLabels(): LabeledElement[] {
    const btns = document.querySelectorAll(
        'button, [role="button"], a[href], input[type="submit"]'
    );
    return Array.from(btns)
        .slice(0, 100)
        .map((el) => ({
            selector: buildSelector(el),
            text: (el.textContent ?? "").trim().slice(0, 200),
        }))
        .filter((lbl) => lbl.text.length > 0);
}

/** Collect heading texts. */
function collectHeadings(): LabeledElement[] {
    const headings = document.querySelectorAll("h1, h2, h3, h4, h5, h6");
    return Array.from(headings)
        .slice(0, 50)
        .map((el) => ({
            selector: buildSelector(el),
            text: (el.textContent ?? "").trim().slice(0, 300),
        }));
}

/** Attempt to collect review text from common review containers. */
function collectReviewText(): string | null {
    const reviewSelectors = [
        '[data-hook="review-body"]',        // Amazon
        ".review-text",
        ".reviewText",
        '[itemprop="reviewBody"]',
        ".comment-body",
        ".user-review",
    ];

    const reviews: string[] = [];
    for (const sel of reviewSelectors) {
        const els = document.querySelectorAll(sel);
        for (const el of els) {
            const text = (el.textContent ?? "").trim();
            if (text.length > 10) {
                reviews.push(text.slice(0, 500));
            }
            if (reviews.length >= 20) break;
        }
        if (reviews.length >= 20) break;
    }

    return reviews.length > 0 ? reviews.join("\n---\n") : null;
}

// ── Checkout Flow Collector ─────────────────────

/** Common selectors for cart/checkout line items. */
const CART_ITEM_SELECTORS = [
    '[data-component-type="s-search-result"]', // Amazon
    ".cart-item", ".basket-item", ".line-item",
    "[data-testid='order-summary-line']",
    ".order-summary-section .product",
    "tr.cart-row", "li.cart-product",
];

const FEE_KEYWORDS = ["fee", "service", "convenience", "booking", "handling", "processing"];
const ADDON_KEYWORDS = ["insurance", "protection", "warranty", "guarantee", "donation"];

/**
 * Attempt to parse prices from text.
 * Finds patterns like $12.99, €9,99, £5.00.
 */
function extractPrice(text: string): number | null {
    const match = text.match(/[\$€£¥]?\s?(\d{1,3}(?:[,. ]\d{3})*(?:[.,]\d{2})?)/);
    if (!match) return null;
    // Normalize commas/dots
    const cleaned = match[1].replace(/[, ]/g, "").replace(",", ".");
    const val = parseFloat(cleaned);
    return isNaN(val) ? null : val;
}

/**
 * Collect checkout flow data by scanning the page for
 * cart items and pricing.
 */
function collectCheckoutFlow(): CheckoutFlowData | null {
    // Quick heuristic: only scan on pages that look like carts/checkouts
    const url = window.location.href.toLowerCase();
    const bodyText = (document.body.innerText ?? "").toLowerCase();
    const isCheckoutPage =
        url.includes("cart") || url.includes("checkout") || url.includes("basket") ||
        url.includes("order") || url.includes("payment") ||
        bodyText.includes("order summary") || bodyText.includes("your cart") ||
        bodyText.includes("subtotal");

    if (!isCheckoutPage) return null;

    const items: CheckoutItem[] = [];

    // Try to find line items
    for (const selector of CART_ITEM_SELECTORS) {
        const elements = document.querySelectorAll(selector);
        for (const el of elements) {
            const text = (el.textContent ?? "").trim();
            const price = extractPrice(text);
            if (price === null) continue;

            // Heuristic: if it has fee/addon keywords, classify accordingly
            const lowerText = text.toLowerCase();
            const isFee = FEE_KEYWORDS.some((k) => lowerText.includes(k));
            const isAddon = ADDON_KEYWORDS.some((k) => lowerText.includes(k));

            // Guess the name from the first line of the element's text
            const name = text.split("\n")[0].trim().slice(0, 100);

            items.push({
                name,
                price,
                // An auto-added addon/fee wasn't explicitly user-added
                is_user_added: !isFee && !isAddon,
                item_type: isFee ? "fee" : isAddon ? "addon" : "product",
            });

            if (items.length >= 30) break;
        }
        if (items.length > 0) break; // use the first matching selector set
    }

    if (items.length === 0) return null;

    // Try to extract total / advertised price
    const totalMatch = bodyText.match(
        /(?:total|grand total|order total)[:\s]*[\$€£¥]?\s?(\d{1,3}(?:[,. ]\d{3})*(?:[.,]\d{2})?)/
    );
    const finalPrice = totalMatch
        ? parseFloat(totalMatch[1].replace(/[, ]/g, ""))
        : items.reduce((sum, it) => sum + it.price, 0);

    const subtotalMatch = bodyText.match(
        /(?:subtotal|sub-total)[:\s]*[\$€£¥]?\s?(\d{1,3}(?:[,. ]\d{3})*(?:[.,]\d{2})?)/
    );
    const advertisedPrice = subtotalMatch
        ? parseFloat(subtotalMatch[1].replace(/[, ]/g, ""))
        : null;

    return {
        advertised_price: advertisedPrice,
        final_price: finalPrice,
        items,
    };
}

// ── Nagging Events Collector ────────────────────

/**
 * Track dynamically added overlays (modals, popups).
 * This runs via a MutationObserver started on script injection.
 */
function isLikelyOverlay(el: Element): boolean {
    if (!(el instanceof HTMLElement)) return false;
    const styles = window.getComputedStyle(el);
    const zIndex = parseInt(styles.zIndex, 10);
    const isFixed = styles.position === "fixed" || styles.position === "absolute";
    const isLargeEnough =
        el.offsetWidth > window.innerWidth * 0.3 &&
        el.offsetHeight > window.innerHeight * 0.3;

    return isFixed && zIndex > 100 && isLargeEnough;
}

function getOverlayText(el: Element): string {
    return (el.textContent ?? "").trim().slice(0, 200);
}

/** Start observing the DOM for dynamically injected overlays. */
function startNaggingObserver(): void {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (!(node instanceof HTMLElement)) continue;

                // Check the added node itself
                if (isLikelyOverlay(node)) {
                    const text = getOverlayText(node);
                    const eventType = inferEventType(text);
                    _naggingEvents.push({
                        type: eventType,
                        text,
                        timestamp: Date.now(),
                    });
                }

                // Also check children (e.g., a wrapper div containing a modal)
                const children = node.querySelectorAll("*");
                for (const child of children) {
                    if (isLikelyOverlay(child)) {
                        const text = getOverlayText(child);
                        const eventType = inferEventType(text);
                        _naggingEvents.push({
                            type: eventType,
                            text,
                            timestamp: Date.now(),
                        });
                        break; // avoid double-counting nested overlays
                    }
                }
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
}

/** Classify the type of nagging event from its text. */
function inferEventType(text: string): NaggingEvent["type"] {
    const lower = text.toLowerCase();
    if (lower.includes("notification") || lower.includes("allow") || lower.includes("subscribe"))
        return "notification_prompt";
    if (lower.includes("download") || lower.includes("app") || lower.includes("install"))
        return "app_install_prompt";
    return "modal";
}

/** Check if there's currently a persistent overlay blocking content. */
function detectPersistentOverlay(): boolean {
    // Look for fixed/absolute elements covering a large portion of the viewport
    const allElements = document.querySelectorAll("*");
    for (const el of allElements) {
        if (isLikelyOverlay(el)) {
            _hasPersistentOverlay = true;
            return true;
        }
    }
    return false;
}

/** Build the nagging events payload. */
function collectNaggingEvents(): NaggingEventsData | null {
    detectPersistentOverlay();

    if (_naggingEvents.length === 0 && !_hasPersistentOverlay) return null;

    return {
        events: [..._naggingEvents],
        has_persistent_overlay: _hasPersistentOverlay,
    };
}

// ── Main entry point ────────────────────────────

/** Main collection entrypoint — collects and sanitizes all signals. */
export function collectPageSignals(): CollectorPayload {
    const domMetadata: DomMetadata = {
        hidden_elements: collectHiddenElements(),
        interactive_elements: collectInteractiveElements(),
        prechecked_inputs: collectPrecheckedInputs(),
        url: window.location.href,
    };

    const textContent: TextContent = {
        button_labels: collectButtonLabels(),
        headings: collectHeadings(),
        body_text: (document.body.innerText ?? "").slice(0, MAX_BODY_TEXT_LENGTH),
    };

    const reviewText = collectReviewText();
    const checkoutFlow = collectCheckoutFlow();
    const naggingEvents = collectNaggingEvents();

    return {
        dom_metadata: sanitizeDomMetadata(domMetadata),
        text_content: sanitizeTextContent(textContent),
        review_text: sanitizeReviewText(reviewText),
        checkout_flow: sanitizeCheckoutFlow(checkoutFlow),
        nagging_events: sanitizeNaggingEvents(naggingEvents),
    };
}

// ── Content-script entry point ──────────────────────────
// Start the nagging observer immediately on injection.
startNaggingObserver();

// Listen for analysis triggers from the service worker.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "COLLECT_SIGNALS") {
        const payload = collectPageSignals();
        sendResponse(payload);
    }
    return true; // keep channel open for async response
});
