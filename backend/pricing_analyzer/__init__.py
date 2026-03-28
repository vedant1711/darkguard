"""
pricing_analyzer — Pricing dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from pricing_analyzer.service import PricingAnalyzerService

AnalyzerRegistry.register(PricingAnalyzerService())
