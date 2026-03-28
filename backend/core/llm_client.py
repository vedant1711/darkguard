"""
core/llm_client.py — Model-agnostic LLM abstraction.

Provides a unified interface for calling LLMs from any analyzer.
Supports multiple providers with automatic fallback:

  - **Gemini** (Google) — always-on default via ``GOOGLE_API_KEY``
  - **NVIDIA NIM** — activated when ``NVIDIA_API_KEY`` is set

Provider routing is purpose-driven:
  - ``text_classification`` → NIM Llama 3.1 70B (if available)
  - ``visual_analysis``     → NIM LLaVA (if available)
  - ``review_analysis``     → NIM Llama 3.1 70B (if available)
  - ``general``             → Gemini (always)

Override via ``LLM_PROVIDER`` env var: ``"auto"`` | ``"gemini"`` | ``"nvidia"``

PII note: callers MUST sanitize prompts via ``core.sanitizer.sanitize_text()``
before calling ``generate()``.  The LLM client does NOT sanitize internally
because prompt structure varies per analyzer.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger(__name__)


# ── Provider ABCs ─────────────────────────────────────────


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'gemini', 'nvidia_nim')."""
        ...

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """Generate a text completion.

        Args:
            prompt: The user prompt / content to analyze.
            system: Optional system prompt for instruction.

        Returns:
            The raw text response from the LLM.

        Raises:
            LLMError: If the API call fails.
        """
        ...


class LLMError(Exception):
    """Raised when an LLM API call fails."""


# ── Gemini Provider ───────────────────────────────────────


class GeminiProvider(LLMProvider):
    """Google Gemini via the ``google-genai`` SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(self, prompt: str, system: str = "") -> str:
        try:
            from google import genai

            client = genai.Client(api_key=self._api_key)
            full_prompt = f"{system}\n\n---\n\n{prompt}" if system else prompt
            response = client.models.generate_content(
                model=self._model,
                contents=full_prompt,
            )
            return response.text or ""
        except Exception as exc:
            raise LLMError(f"Gemini API call failed: {exc}") from exc


# ── NVIDIA NIM Provider ───────────────────────────────────


# Default NIM models per purpose
NIM_MODELS: dict[str, str] = {
    "text_classification": "meta/llama-3.1-70b-instruct",
    "visual_analysis": "liuhaotian/llava-v1.6-mistral-7b",
    "review_analysis": "meta/llama-3.1-70b-instruct",
    "general": "meta/llama-3.1-70b-instruct",
}

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaNIMProvider(LLMProvider):
    """NVIDIA NIM via OpenAI-compatible endpoint."""

    def __init__(
        self, api_key: str, model: str = "meta/llama-3.1-70b-instruct"
    ) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "nvidia_nim"

    async def generate(self, prompt: str, system: str = "") -> str:
        try:
            from openai import OpenAI

            client = OpenAI(
                base_url=NIM_BASE_URL,
                api_key=self._api_key,
            )

            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            completion = client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
            )
            return completion.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"NVIDIA NIM API call failed: {exc}") from exc


# ── Factory ───────────────────────────────────────────────


def get_llm_client(purpose: str = "general") -> LLMProvider:
    """Return the best LLM provider for the given purpose.

    Provider selection logic:
      1. If ``LLM_PROVIDER=gemini``  → always Gemini
      2. If ``LLM_PROVIDER=nvidia``  → always NIM (error if no key)
      3. If ``LLM_PROVIDER=auto`` (default):
         - Use NIM for the purpose if ``NVIDIA_API_KEY`` is set
         - Otherwise fall back to Gemini

    Args:
        purpose: One of ``"text_classification"``, ``"visual_analysis"``,
                 ``"review_analysis"``, ``"general"``.

    Returns:
        An ``LLMProvider`` instance ready to call.

    Raises:
        LLMError: If no API key is configured for any provider.
    """
    provider_override = getattr(settings, "LLM_PROVIDER", "auto").lower()
    google_key = getattr(settings, "GOOGLE_API_KEY", "")
    nvidia_key = getattr(settings, "NVIDIA_API_KEY", "")

    if provider_override == "nvidia":
        if not nvidia_key:
            raise LLMError(
                "LLM_PROVIDER is set to 'nvidia' but NVIDIA_API_KEY is not configured."
            )
        model = NIM_MODELS.get(purpose, NIM_MODELS["general"])
        logger.info("LLM provider: NVIDIA NIM (%s) for purpose=%s", model, purpose)
        return NvidiaNIMProvider(api_key=nvidia_key, model=model)

    if provider_override == "gemini":
        if not google_key:
            raise LLMError(
                "LLM_PROVIDER is set to 'gemini' but GOOGLE_API_KEY is not configured."
            )
        logger.info("LLM provider: Gemini for purpose=%s", purpose)
        return GeminiProvider(api_key=google_key)

    # Auto mode: prefer NIM for specific purposes, Gemini as fallback
    if nvidia_key and purpose in NIM_MODELS and purpose != "general":
        model = NIM_MODELS[purpose]
        logger.info(
            "LLM provider (auto): NVIDIA NIM (%s) for purpose=%s", model, purpose
        )
        return NvidiaNIMProvider(api_key=nvidia_key, model=model)

    if google_key:
        logger.info("LLM provider (auto): Gemini for purpose=%s", purpose)
        return GeminiProvider(api_key=google_key)

    raise LLMError(
        "No LLM API key configured. Set GOOGLE_API_KEY or NVIDIA_API_KEY "
        "in your .env file."
    )
