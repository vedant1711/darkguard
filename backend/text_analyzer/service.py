"""
text_analyzer/service.py — Text Analyzer Service.

Pattern-matching / NLP rules for detecting dark patterns in text:
- Confirmshaming (guilt-tripping decline copy)
- Urgency / scarcity language
- Misdirection (misleading button labels)
- Trick wording (double negatives, ambiguous opt-in/out language)
- Forced action (requiring sign-up or account to access content)

Standalone module — imports only from ``core.*``.
"""

from __future__ import annotations

import re

from core.interfaces import BaseAnalyzer
from core.models import Detection
from text_analyzer.interfaces import LabeledElement, TextPayload


# ── Pattern libraries ─────────────────────────────────────

CONFIRMSHAMING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"no\s*,?\s*i\s+don'?t\s+want", re.IGNORECASE),
    re.compile(r"no\s+thanks?\s*,?\s+i('?d)?\s*(rather|prefer|like)", re.IGNORECASE),
    re.compile(r"i\s+don'?t\s+(care|like|want)\s+(about\s+|to\s+)?(sav|deal|discount|money)", re.IGNORECASE),
    re.compile(r"i('?ll)?\s*(pay|stay)\s+(full\s+price|more)", re.IGNORECASE),
    re.compile(r"no\s*,?\s*i\s+hate\s+(saving|money)", re.IGNORECASE),
    re.compile(r"i\s+prefer\s+not\s+to\s+save", re.IGNORECASE),
]

URGENCY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"only\s+\d+\s+(left|remaining|available)", re.IGNORECASE),
    re.compile(r"(offer|sale|deal|discount)\s+(expires?|ends?)\s+(soon|today|in\s+\d)", re.IGNORECASE),
    re.compile(r"(hurry|act\s+now|don'?t\s+miss|limited\s+time)", re.IGNORECASE),
    re.compile(r"\d+\s+(people|others?)\s+(are\s+)?(viewing|watching|looking)", re.IGNORECASE),
    re.compile(r"(selling|going)\s+fast", re.IGNORECASE),
    re.compile(r"(last|final)\s+chance", re.IGNORECASE),
    # Travel / booking specific patterns
    re.compile(r"\d+\s+(people|guests?|travell?ers?)\s+(booked|reserved)\s+(in|over)\s+(the\s+)?(last|past)", re.IGNORECASE),
    re.compile(r"(in\s+)?high\s+demand", re.IGNORECASE),
    re.compile(r"only\s+\d+\s+(rooms?|seats?|tickets?|spots?|units?)\s+(left|remaining|available)", re.IGNORECASE),
    re.compile(r"prices?\s+(may|might|will|could)\s+(increase|go\s+up|rise)", re.IGNORECASE),
    re.compile(r"(very|super|extremely|incredibly)\s+popular", re.IGNORECASE),
    re.compile(r"(booked|sold|purchased)\s+\d+\s+times?\s+(today|this\s+week|recently)", re.IGNORECASE),
]

MISDIRECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"^continue$", re.IGNORECASE),
        "A button labeled 'Continue' may actually mean 'Subscribe' or 'Accept'.",
    ),
    (
        re.compile(r"^(get\s+started|start\s+now)$", re.IGNORECASE),
        "Generic action label may hide subscription or commitment.",
    ),
    (
        re.compile(r"^(claim|unlock|activate)\b", re.IGNORECASE),
        "Action-oriented label may disguise paid commitment or data collection.",
    ),
]

TRICK_WORDING_PATTERNS: list[re.Pattern[str]] = [
    # Double negatives
    re.compile(r"un(check|tick|select)\s+(to\s+)?(not|avoid|prevent|stop)", re.IGNORECASE),
    re.compile(r"(don'?t|do\s+not)\s+un(check|subscribe|select)", re.IGNORECASE),
    # Ambiguous toggle language
    re.compile(r"(opt\s+out|turn\s+off)\s+(of\s+)?(not\s+)?(receiving|sharing|sending)", re.IGNORECASE),
    # Confusing consent phrasing
    re.compile(r"by\s+(clicking|continuing|proceeding|signing).*you\s+(agree|consent|accept)", re.IGNORECASE),
    # Misleading negative phrasing
    re.compile(r"(no|don'?t)\s*,?\s*i\s+(don'?t\s+)?want\s+to\s+(keep|continue|stay|remain)", re.IGNORECASE),
]

FORCED_ACTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(sign\s+up|create\s+(an?\s+)?account|register|log\s+in)\s+(to\s+)?(view|see|access|continue|read|download|unlock)", re.IGNORECASE),
    re.compile(r"(you\s+must|you\s+need\s+to|please)\s+(sign\s+up|create|register|log\s+in)", re.IGNORECASE),
    re.compile(r"(join|sign\s+up)\s+(for\s+)?free\s+to\s+(continue|access|view|unlock)", re.IGNORECASE),
    re.compile(r"(only|available)\s+(for|to)\s+(members?|subscribers?|registered)", re.IGNORECASE),
]


# TODO(roberta): Replace regex patterns with a fine-tuned RoBERTa classifier.
# Integration point: load a HuggingFace `transformers` pipeline here for
# confirmshaming / urgency / misdirection classification. The regex rules
# above should remain as a fast-path fallback when the model is unavailable.
# Expected model: fine-tuned roberta-base on dark-pattern text corpus.
# See: https://huggingface.co/docs/transformers/model_doc/roberta


class TextAnalyzerService(BaseAnalyzer):
    """Analyzes visible text for dark-pattern signals."""

    @property
    def name(self) -> str:
        return "text"

    @property
    def required_payload_keys(self) -> list[str]:
        return ["text_content"]

    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        detections: list[Detection] = []

        # Convert raw dict → typed TextPayload
        text_payload = self._parse_payload(payload)
        if text_payload is None:
            return detections

        detections.extend(self._check_confirmshaming(text_payload.button_labels))
        detections.extend(self._check_misdirection(text_payload.button_labels))
        detections.extend(self._check_urgency(text_payload.body_text))
        detections.extend(self._check_trick_wording(text_payload.body_text, text_payload.button_labels))
        detections.extend(self._check_forced_action(text_payload.body_text, text_payload.button_labels))

        return detections

    def _parse_payload(self, payload: dict[str, object]) -> TextPayload | None:
        """Convert raw payload dict → typed TextPayload."""
        text_content = payload.get("text_content", {})
        if not isinstance(text_content, dict):
            return None

        raw_labels = text_content.get("button_labels", [])
        raw_headings = text_content.get("headings", [])
        body_text = str(text_content.get("body_text", ""))

        labels = [
            LabeledElement(
                selector=str(lbl.get("selector", "")),
                text=str(lbl.get("text", "")),
            )
            for lbl in (raw_labels if isinstance(raw_labels, list) else [])
            if isinstance(lbl, dict)
        ]

        headings = [
            LabeledElement(
                selector=str(h.get("selector", "")),
                text=str(h.get("text", "")),
            )
            for h in (raw_headings if isinstance(raw_headings, list) else [])
            if isinstance(h, dict)
        ]

        return TextPayload(
            button_labels=labels,
            headings=headings,
            body_text=body_text,
        )

    def _check_confirmshaming(
        self, labels: list[LabeledElement]
    ) -> list[Detection]:
        """Detect guilt-tripping decline copy on buttons/links."""
        detections: list[Detection] = []
        for lbl in labels:
            for pattern in CONFIRMSHAMING_PATTERNS:
                if pattern.search(lbl.text):
                    detections.append(
                        Detection(
                            category="confirmshaming",
                            element_selector=lbl.selector,
                            confidence=0.85,
                            explanation=(
                                f'The decline option uses guilt-tripping language: "{lbl.text}"'
                            ),
                            severity="medium",
                            analyzer_name=self.name,
                            platform_context="ecommerce",
                            regulation_refs=["FTC-S5", "DSA-Art25"],
                        )
                    )
                    break  # one match per label
        return detections

    def _check_urgency(self, body_text: str) -> list[Detection]:
        """Detect artificial urgency/scarcity language."""
        detections: list[Detection] = []
        for pattern in URGENCY_PATTERNS:
            match = pattern.search(body_text)
            if match:
                snippet = body_text[max(0, match.start() - 20):match.end() + 20]
                detections.append(
                    Detection(
                        category="urgency_scarcity",
                        element_selector="body",
                        confidence=0.7,
                        explanation=(
                            f'Urgency/scarcity language detected: "…{snippet.strip()}…"'
                        ),
                        severity="low",
                        analyzer_name=self.name,
                        platform_context="ecommerce",
                        regulation_refs=["FTC-S5"],
                    )
                )
        return detections

    def _check_misdirection(
        self, labels: list[LabeledElement]
    ) -> list[Detection]:
        """Detect misleading button labels."""
        detections: list[Detection] = []
        for lbl in labels:
            text = lbl.text.strip()
            for pattern, explanation in MISDIRECTION_PATTERNS:
                if pattern.match(text):
                    detections.append(
                        Detection(
                            category="misdirection",
                            element_selector=lbl.selector,
                            confidence=0.6,
                            explanation=explanation,
                            severity="low",
                            analyzer_name=self.name,
                            platform_context="general",
                            regulation_refs=["DSA-Art25"],
                        )
                    )
                    break
        return detections

    def _check_trick_wording(
        self, body_text: str, labels: list[LabeledElement]
    ) -> list[Detection]:
        """Detect confusing double negatives and ambiguous opt-in/out language."""
        detections: list[Detection] = []
        # Check body text
        for pattern in TRICK_WORDING_PATTERNS:
            match = pattern.search(body_text)
            if match:
                snippet = body_text[max(0, match.start() - 30):match.end() + 30]
                detections.append(
                    Detection(
                        category="trick_wording",
                        element_selector="body",
                        confidence=0.75,
                        explanation=(
                            f'Confusing or trick wording detected: "…{snippet.strip()}…". '
                            f'This kind of phrasing can mislead users into making unintended choices.'
                        ),
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="general",
                        regulation_refs=["FTC-S5", "UCPD"],
                    )
                )
        # Check button labels
        for lbl in labels:
            for pattern in TRICK_WORDING_PATTERNS:
                if pattern.search(lbl.text):
                    detections.append(
                        Detection(
                            category="trick_wording",
                            element_selector=lbl.selector,
                            confidence=0.8,
                            explanation=(
                                f'This button/link uses confusing wording: "{lbl.text[:80]}". '
                                f'Watch out for double negatives or ambiguous phrasing.'
                            ),
                            severity="medium",
                            analyzer_name=self.name,
                            platform_context="general",
                            regulation_refs=["FTC-S5", "UCPD"],
                        )
                    )
                    break
        return detections

    def _check_forced_action(
        self, body_text: str, labels: list[LabeledElement]
    ) -> list[Detection]:
        """Detect forced account creation or sign-up to access content."""
        detections: list[Detection] = []
        for pattern in FORCED_ACTION_PATTERNS:
            match = pattern.search(body_text)
            if match:
                snippet = body_text[max(0, match.start() - 20):match.end() + 20]
                detections.append(
                    Detection(
                        category="forced_action",
                        element_selector="body",
                        confidence=0.7,
                        explanation=(
                            f'Forced action detected: "…{snippet.strip()}…". '
                            f'The site may be requiring account creation or sign-up '
                            f'to access content that could be available without it.'
                        ),
                        severity="medium",
                        analyzer_name=self.name,
                        platform_context="general",
                        regulation_refs=["GDPR-Art7", "DSA-Art25"],
                    )
                )
        # Check buttons
        for lbl in labels:
            for pattern in FORCED_ACTION_PATTERNS:
                if pattern.search(lbl.text):
                    detections.append(
                        Detection(
                            category="forced_action",
                            element_selector=lbl.selector,
                            confidence=0.7,
                            explanation=(
                                f'This element requires an action to continue: "{lbl.text[:80]}". '
                                f'Users may be forced to sign up or create an account unnecessarily.'
                            ),
                            severity="medium",
                            analyzer_name=self.name,
                            platform_context="general",
                            regulation_refs=["GDPR-Art7", "DSA-Art25"],
                        )
                    )
                    break
        return detections
