"""
consent_analyzer — Consent dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from consent_analyzer.service import ConsentAnalyzerService
from core.registry import AnalyzerRegistry

AnalyzerRegistry.register(ConsentAnalyzerService())
