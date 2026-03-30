// ──────────────────────────────────────────────
// DarkGuard — Shared TypeScript interfaces
// ──────────────────────────────────────────────

/** Severity levels for a detected dark pattern. */
export type Severity = "low" | "medium" | "high";

/** User feedback values for model fine-tuning. */
export type UserFeedback = "false_positive" | "confirmed" | null;

/** Dark-pattern taxonomy categories. */
export type DarkPatternCategory =
    // Phase 1 (original)
    | "urgency_scarcity"
    | "confirmshaming"
    | "visual_interference"
    | "preselection"
    | "hidden_costs"
    | "misdirection"
    | "fake_social_proof"
    // Phase 2 (consent)
    | "asymmetric_choice"
    | "prechecked_consent"
    // Phase 2 (checkout)
    | "basket_sneaking"
    | "drip_pricing"
    // Phase 2 (subscription)
    | "roach_motel"
    | "forced_continuity"
    | "plan_comparison_trick"
    // Phase 2 (privacy)
    | "privacy_zuckering"
    // Phase 2 (nagging)
    | "notification_inflation"
    | "persistent_nagging"
    // Phase 2 (pricing)
    | "price_anchoring"
    | "bnpl_deception"
    | "intermediate_currency";

/** A single dark-pattern detection returned by the backend. */
export interface Detection {
    category: DarkPatternCategory;
    element_selector: string;
    confidence: number;
    explanation: string;
    severity: Severity;
    corroborated: boolean;
    user_feedback: UserFeedback;
    /** Which analyzer produced this detection. */
    analyzer_name: string;
    /** Context where the pattern was found. */
    platform_context: string;
    /** Regulatory references (e.g., GDPR-Art7, FTC-S5). */
    regulation_refs: string[];
}

/** Payload sent from the content script to the service worker. */
export interface CollectorPayload {
    dom_metadata: DomMetadata;
    text_content: TextContent;
    review_text: string | null;
    checkout_flow: CheckoutFlowData | null;
    nagging_events: NaggingEventsData | null;
}

/** DOM metadata collected by the content script. */
export interface DomMetadata {
    /** Hidden elements (display:none, visibility:hidden, opacity:0). */
    hidden_elements: ElementInfo[];
    /** Buttons/CTAs with their computed styles for size-ratio analysis. */
    interactive_elements: ElementInfo[];
    /** Pre-checked checkboxes/radios. */
    prechecked_inputs: ElementInfo[];
    /** Page URL for context. */
    url: string;
}

/** Information about a single DOM element. */
export interface ElementInfo {
    selector: string;
    tag_name: string;
    text_content: string;
    attributes: Record<string, string>;
    bounding_rect: BoundingRect;
    computed_styles: ComputedStyleInfo;
}

/** Bounding rectangle of an element. */
export interface BoundingRect {
    x: number;
    y: number;
    width: number;
    height: number;
}

/** Computed style subset relevant to dark-pattern detection. */
export interface ComputedStyleInfo {
    color: string;
    background_color: string;
    font_size: string;
    opacity: string;
    display: string;
    visibility: string;
}

/** Visible text content extracted from the page. */
export interface TextContent {
    /** All button / CTA label texts. */
    button_labels: LabeledElement[];
    /** Headings and prominent text. */
    headings: LabeledElement[];
    /** Body text paragraphs (first 5000 chars). */
    body_text: string;
}

/** A text label tied to a DOM selector. */
export interface LabeledElement {
    selector: string;
    text: string;
}

// ── Phase 2 payload types ───────────────────────

/** A single line-item in a checkout flow. */
export interface CheckoutItem {
    name: string;
    price: number;
    is_user_added: boolean;
    item_type: "product" | "addon" | "fee" | "tax" | "shipping";
}

/** Checkout flow data for the checkout_flow_analyzer. */
export interface CheckoutFlowData {
    advertised_price: number | null;
    final_price: number;
    items: CheckoutItem[];
}

/** A single interruptive event tracked by the nagging collector. */
export interface NaggingEvent {
    type: "modal" | "notification_prompt" | "app_install_prompt" | "overlay";
    text: string;
    timestamp: number;
}

/** Nagging events data for the nagging_analyzer. */
export interface NaggingEventsData {
    events: NaggingEvent[];
    has_persistent_overlay: boolean;
}

/** Full request payload sent to the backend API. */
export interface AnalyzeRequest {
    dom_metadata: DomMetadata;
    text_content: TextContent;
    screenshot_b64: string;
    review_text: string | null;
    checkout_flow: CheckoutFlowData | null;
    nagging_events: NaggingEventsData | null;
    url: string;
}

/** Response from the backend API. */
export interface AnalyzeResponse {
    detections: Detection[];
}

/** Message types for chrome.runtime messaging. */
export type MessageType =
    | { type: "ANALYZE_PAGE"; payload: CollectorPayload }
    | { type: "DETECTIONS_READY"; detections: Detection[] };
