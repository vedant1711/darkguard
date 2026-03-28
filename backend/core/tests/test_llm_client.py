"""Tests for the model-agnostic LLM client."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from core.llm_client import (
    GeminiProvider,
    LLMError,
    NvidiaNIMProvider,
    get_llm_client,
)


class TestGetLLMClient:
    """Tests for get_llm_client() provider routing."""

    @patch("core.llm_client.settings")
    def test_gemini_default_when_only_google_key(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "auto"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = ""  # type: ignore[attr-defined]

        client = get_llm_client("text_classification")
        assert isinstance(client, GeminiProvider)

    @patch("core.llm_client.settings")
    def test_nim_preferred_for_text_classification(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "auto"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = "test-nvidia-key"  # type: ignore[attr-defined]

        client = get_llm_client("text_classification")
        assert isinstance(client, NvidiaNIMProvider)

    @patch("core.llm_client.settings")
    def test_nim_preferred_for_visual_analysis(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "auto"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = "test-nvidia-key"  # type: ignore[attr-defined]

        client = get_llm_client("visual_analysis")
        assert isinstance(client, NvidiaNIMProvider)

    @patch("core.llm_client.settings")
    def test_gemini_for_general_even_with_nim(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "auto"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = "test-nvidia-key"  # type: ignore[attr-defined]

        client = get_llm_client("general")
        assert isinstance(client, GeminiProvider)

    @patch("core.llm_client.settings")
    def test_force_gemini_override(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "gemini"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = "test-nvidia-key"  # type: ignore[attr-defined]

        client = get_llm_client("text_classification")
        assert isinstance(client, GeminiProvider)

    @patch("core.llm_client.settings")
    def test_force_nvidia_override(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "nvidia"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = "test-nvidia-key"  # type: ignore[attr-defined]

        client = get_llm_client("general")
        assert isinstance(client, NvidiaNIMProvider)

    @patch("core.llm_client.settings")
    def test_no_keys_raises(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "auto"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = ""  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = ""  # type: ignore[attr-defined]

        with pytest.raises(LLMError, match="No LLM API key configured"):
            get_llm_client()

    @patch("core.llm_client.settings")
    def test_nvidia_forced_without_key_raises(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "nvidia"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = ""  # type: ignore[attr-defined]

        with pytest.raises(LLMError, match="NVIDIA_API_KEY is not configured"):
            get_llm_client()

    @patch("core.llm_client.settings")
    def test_gemini_forced_without_key_raises(self, mock_settings: object) -> None:
        mock_settings.LLM_PROVIDER = "gemini"  # type: ignore[attr-defined]
        mock_settings.GOOGLE_API_KEY = ""  # type: ignore[attr-defined]
        mock_settings.NVIDIA_API_KEY = "test-nvidia-key"  # type: ignore[attr-defined]

        with pytest.raises(LLMError, match="GOOGLE_API_KEY is not configured"):
            get_llm_client()
