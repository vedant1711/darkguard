"""
core/serializers.py — DRF serializers for the /api/analyze endpoint.
"""

from __future__ import annotations

from rest_framework import serializers


# ── Request serializers ──────────────────────────────────


class BoundingRectSerializer(serializers.Serializer[dict[str, float]]):
    x = serializers.FloatField()
    y = serializers.FloatField()
    width = serializers.FloatField()
    height = serializers.FloatField()


class ComputedStyleSerializer(serializers.Serializer[dict[str, str]]):
    color = serializers.CharField()
    background_color = serializers.CharField()
    font_size = serializers.CharField()
    opacity = serializers.CharField()
    display = serializers.CharField()
    visibility = serializers.CharField()


class ElementInfoSerializer(serializers.Serializer[dict[str, object]]):
    selector = serializers.CharField()
    tag_name = serializers.CharField()
    text_content = serializers.CharField(allow_blank=True)
    attributes = serializers.DictField(child=serializers.CharField())
    bounding_rect = BoundingRectSerializer()
    computed_styles = ComputedStyleSerializer()


class DomMetadataSerializer(serializers.Serializer[dict[str, object]]):
    hidden_elements = ElementInfoSerializer(many=True)
    interactive_elements = ElementInfoSerializer(many=True)
    prechecked_inputs = ElementInfoSerializer(many=True)
    url = serializers.URLField()


class LabeledElementSerializer(serializers.Serializer[dict[str, str]]):
    selector = serializers.CharField()
    text = serializers.CharField()


class TextContentSerializer(serializers.Serializer[dict[str, object]]):
    button_labels = LabeledElementSerializer(many=True)
    headings = LabeledElementSerializer(many=True)
    body_text = serializers.CharField(allow_blank=True)


class AnalyzeRequestSerializer(serializers.Serializer[dict[str, object]]):
    dom_metadata = DomMetadataSerializer()
    text_content = TextContentSerializer()
    screenshot_b64 = serializers.CharField()
    review_text = serializers.CharField(allow_null=True, required=False)
    url = serializers.URLField()


# ── Response serializers ─────────────────────────────────


class DetectionSerializer(serializers.Serializer[dict[str, object]]):
    category = serializers.CharField()
    element_selector = serializers.CharField()
    confidence = serializers.FloatField(min_value=0.0, max_value=1.0)
    explanation = serializers.CharField()
    severity = serializers.ChoiceField(choices=["low", "medium", "high"])
    corroborated = serializers.BooleanField()
    user_feedback = serializers.ChoiceField(
        choices=["false_positive", "confirmed"],
        allow_null=True,
    )
    analyzer_name = serializers.CharField(allow_blank=True, default="")
    platform_context = serializers.CharField(default="general")
    regulation_refs = serializers.ListField(
        child=serializers.CharField(), default=list
    )


class AnalyzeResponseSerializer(serializers.Serializer[dict[str, object]]):
    detections = DetectionSerializer(many=True)
