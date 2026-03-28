"""
text_analyzer — Text dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from text_analyzer.service import TextAnalyzerService

AnalyzerRegistry.register(TextAnalyzerService())
