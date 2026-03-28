"""
visual_analyzer — Visual dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from visual_analyzer.service import VisualAnalyzerService

AnalyzerRegistry.register(VisualAnalyzerService())
