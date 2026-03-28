"""
core/registry.py — Dynamic Analyzer Registry.

Auto-discovers and manages analyzer instances.  Each analyzer module's
``__init__.py`` registers its service via ``AnalyzerRegistry.register()``.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from core.interfaces import BaseAnalyzer

logger = logging.getLogger(__name__)


class AnalyzerRegistry:
    """Central registry for all dark-pattern analyzers.

    Modules register themselves on import; ``discover()`` triggers the
    import of every ``*_analyzer`` package found under ``backend/``.
    """

    _analyzers: dict[str, BaseAnalyzer] = {}

    @classmethod
    def register(cls, analyzer: BaseAnalyzer) -> None:
        """Register an analyzer instance.

        Raises:
            ValueError: If an analyzer with the same name is already registered.
        """
        name = analyzer.name
        if name in cls._analyzers:
            raise ValueError(
                f"Analyzer '{name}' is already registered. "
                f"Each analyzer must have a unique name."
            )
        cls._analyzers[name] = analyzer
        logger.info("Registered analyzer: %s", name)

    @classmethod
    def get_all(cls) -> dict[str, BaseAnalyzer]:
        """Return all registered analyzers."""
        return dict(cls._analyzers)

    @classmethod
    def get(cls, name: str) -> BaseAnalyzer | None:
        """Return a specific analyzer by name, or None."""
        return cls._analyzers.get(name)

    @classmethod
    def discover(cls) -> None:
        """Auto-import all ``*_analyzer`` packages to trigger registration.

        Scans the backend root directory for directories ending in
        ``_analyzer`` and imports them.  Each package is expected to
        call ``AnalyzerRegistry.register()`` in its ``__init__.py``.
        """
        import sys

        backend_root = Path(__file__).resolve().parent.parent

        for item in sorted(backend_root.iterdir()):
            if (
                item.is_dir()
                and item.name.endswith("_analyzer")
                and (item / "__init__.py").exists()
            ):
                module_name = item.name
                try:
                    if module_name in sys.modules:
                        # Module already imported — reload to re-trigger
                        # registration (needed after clear() in tests).
                        mod = sys.modules[module_name]
                        try:
                            importlib.reload(mod)
                        except ValueError:
                            # Already registered — skip silently
                            pass
                    else:
                        importlib.import_module(module_name)
                    logger.debug("Discovered analyzer package: %s", module_name)
                except Exception:
                    logger.exception(
                        "Failed to import analyzer package: %s", module_name
                    )

    @classmethod
    def clear(cls) -> None:
        """Clear all registered analyzers (used in tests)."""
        cls._analyzers.clear()
