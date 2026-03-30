// ──────────────────────────────────────────────
// DarkGuard — PII Sanitizer
// Strips sensitive data before payloads leave the browser.
// ──────────────────────────────────────────────

import type {
    DomMetadata,
    TextContent,
    ElementInfo,
    CheckoutFlowData,
    NaggingEventsData,
} from "../types/index";

const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const PHONE_REGEX = /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
const SSN_REGEX = /\b\d{3}-\d{2}-\d{4}\b/g;
const CC_REGEX = /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g;

const PII_REPLACEMENT = "[REDACTED]";

/** Attributes that should always be stripped from element payloads. */
const SENSITIVE_ATTRS = ["value", "placeholder", "data-pii", "data-email", "data-phone"];

/** Input types whose text content should be fully redacted. */
const SENSITIVE_INPUT_TYPES = ["password", "email", "tel", "ssn"];

function redactPiiFromText(text: string): string {
    return text
        .replace(EMAIL_REGEX, PII_REPLACEMENT)
        .replace(PHONE_REGEX, PII_REPLACEMENT)
        .replace(SSN_REGEX, PII_REPLACEMENT)
        .replace(CC_REGEX, PII_REPLACEMENT);
}

function sanitizeElementInfo(el: ElementInfo): ElementInfo {
    const sanitizedAttrs = { ...el.attributes };

    // Strip sensitive attribute values
    for (const attr of SENSITIVE_ATTRS) {
        if (attr in sanitizedAttrs) {
            sanitizedAttrs[attr] = PII_REPLACEMENT;
        }
    }

    // Redact text content of sensitive input types
    const inputType = (el.attributes["type"] ?? "").toLowerCase();
    const isSensitiveInput =
        el.tag_name.toLowerCase() === "input" &&
        SENSITIVE_INPUT_TYPES.includes(inputType);

    return {
        ...el,
        text_content: isSensitiveInput
            ? PII_REPLACEMENT
            : redactPiiFromText(el.text_content),
        attributes: sanitizedAttrs,
    };
}

/** Sanitize DOM metadata: strip PII from all element info. */
export function sanitizeDomMetadata(meta: DomMetadata): DomMetadata {
    return {
        ...meta,
        hidden_elements: meta.hidden_elements.map(sanitizeElementInfo),
        interactive_elements: meta.interactive_elements.map(sanitizeElementInfo),
        prechecked_inputs: meta.prechecked_inputs.map(sanitizeElementInfo),
    };
}

/** Sanitize text content: redact PII from body text and labels. */
export function sanitizeTextContent(content: TextContent): TextContent {
    return {
        button_labels: content.button_labels.map((lbl) => ({
            ...lbl,
            text: redactPiiFromText(lbl.text),
        })),
        headings: content.headings.map((h) => ({
            ...h,
            text: redactPiiFromText(h.text),
        })),
        body_text: redactPiiFromText(content.body_text),
    };
}

/** Sanitize review text: redact PII from review content. */
export function sanitizeReviewText(text: string | null): string | null {
    if (text === null) return null;
    return redactPiiFromText(text);
}

/** Sanitize checkout flow data: redact PII from item names. */
export function sanitizeCheckoutFlow(
    data: CheckoutFlowData | null
): CheckoutFlowData | null {
    if (!data) return null;
    return {
        ...data,
        items: data.items.map((item) => ({
            ...item,
            name: redactPiiFromText(item.name),
        })),
    };
}

/** Sanitize nagging events: redact PII from event text. */
export function sanitizeNaggingEvents(
    data: NaggingEventsData | null
): NaggingEventsData | null {
    if (!data) return null;
    return {
        ...data,
        events: data.events.map((ev) => ({
            ...ev,
            text: redactPiiFromText(ev.text),
        })),
    };
}
