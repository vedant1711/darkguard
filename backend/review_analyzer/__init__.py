"""
review_analyzer — Review dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from review_analyzer.service import ReviewAnalyzerService

AnalyzerRegistry.register(ReviewAnalyzerService())
