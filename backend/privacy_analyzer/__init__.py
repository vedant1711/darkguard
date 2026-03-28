"""
privacy_analyzer — Privacy dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from privacy_analyzer.service import PrivacyAnalyzerService

AnalyzerRegistry.register(PrivacyAnalyzerService())
