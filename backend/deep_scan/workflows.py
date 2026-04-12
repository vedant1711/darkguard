"""
deep_scan/workflows.py — Predefined workflow definitions for deep scanning.

Each workflow is a sequence of intent-driven steps that the engine will
attempt to execute using heuristic element matching (CSS selectors + text).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """A single step in a deep scan workflow."""
    action: str            # "navigate", "find_and_click", "analyze_only", "analyze_banner"
    intent: str            # Human-readable intent: "Find and use the search functionality"
    hints: list[str] = field(default_factory=list)  # CSS/text hints to find the target
    type_text: str = ""    # Text to type (for search actions)
    max_wait_ms: int = 10_000


@dataclass
class WorkflowDefinition:
    """A named workflow with a description and steps."""
    name: str
    description: str
    icon: str
    steps: list[WorkflowStep]


# ── Payment safety blocklist ─────────────────────────────
# The engine will NEVER click elements matching these patterns.
PAYMENT_BLOCKLIST = [
    "pay now", "place order", "submit payment", "complete purchase",
    "confirm payment", "process payment", "buy now", "checkout",
    "submit order", "finalize order", "make payment",
]


WORKFLOWS: dict[str, WorkflowDefinition] = {
    "search_book": WorkflowDefinition(
        name="Search & Book",
        description="Search for a product/service, browse results, select one, proceed toward checkout. Stops before any payment.",
        icon="🔍",
        steps=[
            WorkflowStep(
                action="navigate",
                intent="Load the homepage",
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Find and interact with the search functionality",
                hints=[
                    "input[type=search]", "[placeholder*=Search]", "[placeholder*=search]",
                    "input[name=q]", "input[name=query]", "input[name=search]",
                    "[aria-label*=Search]", "[aria-label*=search]",
                ],
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Select the first result or listing",
                hints=[
                    ".result a", ".listing a", ".product-card a", ".card a",
                    "[data-testid*=result]", "[data-testid*=listing]",
                    "article a", ".search-result a",
                ],
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Add to cart or proceed to book",
                hints=[
                    "button:has-text('Book')", "button:has-text('Add to cart')",
                    "button:has-text('Reserve')", "button:has-text('Select')",
                    "button:has-text('Add to bag')", "button:has-text('Add')",
                    "[data-testid*=book]", "[data-testid*=cart]",
                ],
            ),
            WorkflowStep(
                action="analyze_only",
                intent="Analyze the checkout/cart page for dark patterns (DO NOT submit payment)",
            ),
        ],
    ),

    "consent_privacy": WorkflowDefinition(
        name="Consent & Privacy",
        description="Interact with cookie/consent banner, navigate to privacy settings, check for preselections and asymmetric choices.",
        icon="🍪",
        steps=[
            WorkflowStep(
                action="navigate",
                intent="Load homepage and look for cookie/consent banner",
            ),
            WorkflowStep(
                action="analyze_only",
                intent="Analyze the cookie consent banner before interacting with it",
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Click 'Manage', 'Settings', or 'Customize' on the cookie banner",
                hints=[
                    "#onetrust-pc-btn-handler", "[id*='cookie'][id*='manage']",
                    "[data-testid*='cookie'][data-testid*='manage']",
                    "button:has-text('Manage')", "button:has-text('Settings')",
                    "button:has-text('Customize')", "button:has-text('Preferences')",
                    "a:has-text('Cookie settings')", "a:has-text('Privacy settings')",
                    "button:has-text('Cookie options')", "button[aria-label*='Manage cookies']",
                ],
            ),
            WorkflowStep(
                action="analyze_only",
                intent="Analyze cookie preferences page for preselected options and asymmetric choices",
            ),
        ],
    ),

    "account_cancel": WorkflowDefinition(
        name="Account & Cancel",
        description="Navigate to account settings and attempt to find cancellation or unsubscribe options. Detects obstruction patterns (roach motel).",
        icon="❌",
        steps=[
            WorkflowStep(
                action="navigate",
                intent="Load homepage",
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Find account or settings link",
                hints=[
                    "a:has-text('Account')", "a:has-text('Settings')",
                    "a:has-text('Profile')", "[aria-label*=account]",
                    "[aria-label*=settings]", "a:has-text('My Account')",
                ],
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Look for subscription or membership section",
                hints=[
                    "a:has-text('Subscription')", "a:has-text('Membership')",
                    "a:has-text('Plan')", "a:has-text('Billing')",
                    "a:has-text('Premium')", "a:has-text('Manage subscription')",
                ],
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Find cancel or unsubscribe option",
                hints=[
                    "a:has-text('Cancel')", "button:has-text('Cancel')",
                    "a:has-text('Unsubscribe')", "a:has-text('Close account')",
                    "a:has-text('Delete account')", "button:has-text('Cancel subscription')",
                ],
            ),
            WorkflowStep(
                action="analyze_only",
                intent="Analyze the cancellation flow for obstruction and roach motel patterns",
            ),
        ],
    ),

    "signup_flow": WorkflowDefinition(
        name="Sign-up Flow",
        description="Navigate to registration and analyze forms for preselections, forced actions, and trick wording.",
        icon="📝",
        steps=[
            WorkflowStep(
                action="navigate",
                intent="Load homepage",
            ),
            WorkflowStep(
                action="find_and_click",
                intent="Find sign-up or register link",
                hints=[
                    "[data-testid*='sign-up']", "[data-testid*='register']",
                    "a:has-text('Sign up')", "a:has-text('Register')",
                    "a:has-text('Create account')", "a:has-text('Get started')",
                    "button:has-text('Sign up')", "button:has-text('Register')",
                    "a:has-text('Join')", "a:has-text('Start free')",
                    "[aria-label*='Sign in or register']",
                ],
            ),
            WorkflowStep(
                action="analyze_only",
                intent="Analyze registration form for preselections, forced actions, and trick wording",
            ),
        ],
    ),
}
