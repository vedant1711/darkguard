"""
nagging_analyzer — Nagging dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from nagging_analyzer.service import NaggingAnalyzerService

AnalyzerRegistry.register(NaggingAnalyzerService())
