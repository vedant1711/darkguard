"""
dom_analyzer — DOM dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from dom_analyzer.service import DomAnalyzerService

AnalyzerRegistry.register(DomAnalyzerService())
