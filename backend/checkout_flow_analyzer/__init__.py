"""
checkout_flow_analyzer — Checkout Flow dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from checkout_flow_analyzer.service import CheckoutFlowAnalyzerService
from core.registry import AnalyzerRegistry

AnalyzerRegistry.register(CheckoutFlowAnalyzerService())
