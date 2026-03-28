"""
subscription_analyzer — Subscription dark-pattern analyzer module.

Auto-registers with the AnalyzerRegistry on import.
"""

from core.registry import AnalyzerRegistry
from subscription_analyzer.service import SubscriptionAnalyzerService

AnalyzerRegistry.register(SubscriptionAnalyzerService())
