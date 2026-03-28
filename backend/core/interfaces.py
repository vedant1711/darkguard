"""
core/interfaces.py — BaseAnalyzer abstract base class.

Every analyzer module inherits from this and implements `analyze()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import Detection


class BaseAnalyzer(ABC):
    """Abstract base class for all dark-pattern analyzers.

    Every analyzer module inherits from this and implements:
    - name: unique identifier (e.g. 'dom', 'text')
    - required_payload_keys: which payload keys the analyzer needs
    - analyze(): the detection logic, converting raw dict → typed payload internally
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this analyzer (e.g. 'dom', 'text')."""
        ...

    @property
    @abstractmethod
    def required_payload_keys(self) -> list[str]:
        """Payload keys this analyzer requires (e.g. ['dom_metadata']).

        The dispatcher will skip this analyzer (with a warning) if any
        required key is missing from the incoming payload.
        """
        ...

    @abstractmethod
    async def analyze(self, payload: dict[str, object]) -> list[Detection]:
        """Analyze a payload and return a list of detections.

        Implementations should convert ``payload`` into their own typed
        dataclass (from their module's ``interfaces.py``) as the first step
        for internal type safety.

        Args:
            payload: The full request payload (each analyzer picks its keys).

        Returns:
            A list of Detection instances found by this analyzer.
        """
        ...
