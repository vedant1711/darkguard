"""
core/views.py — POST /api/analyze endpoint.

Accepts the full analysis payload, sanitizes it server-side,
dispatches to all registered analyzers, and returns merged detections.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from core.dispatcher import dispatch
from core.registry import AnalyzerRegistry
from core.sanitizer import sanitize_payload
from core.serializers import AnalyzeRequestSerializer, AnalyzeResponseSerializer

# Ensure all analyzer packages are discovered on first import
AnalyzerRegistry.discover()


@api_view(["POST"])
def analyze(request: Request) -> Response:
    """POST /api/analyze — run all dark-pattern analyzers."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    payload: dict[str, object] = serializer.validated_data  # type: ignore[assignment]

    # Layer 2: server-side PII re-sanitization (defense-in-depth)
    payload = sanitize_payload(payload)

    # Dispatch to all registered analyzers
    detections = asyncio.run(dispatch(payload))

    response_data = {
        "detections": [asdict(d) for d in detections],
    }

    out = AnalyzeResponseSerializer(data=response_data)
    out.is_valid(raise_exception=True)

    return Response(out.validated_data, status=status.HTTP_200_OK)
