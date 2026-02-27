"""
Single shared Jinja2Templates instance with all custom filters registered.

All routers import `templates` from here so filters are always available.
"""

from datetime import datetime
from typing import Optional

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


# ── Custom filters ─────────────────────────────────────────────────────────────

def _format_date(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    return dt.strftime("%b %d, %Y")


def _days_label(days: Optional[int]) -> str:
    if days is None:
        return "—"
    if days < 0:
        return f"Expired {abs(days)}d ago"
    if days == 0:
        return "Expires today"
    return f"{days}d remaining"


def _risk_badge(risk_level: str) -> str:
    return {
        "HIGH":   "badge-risk-high",
        "MEDIUM": "badge-risk-medium",
        "LOW":    "badge-risk-low",
        "NONE":   "badge-risk-none",
    }.get(str(risk_level), "badge-risk-none")


def _audience_label(audience: str) -> str:
    return {
        "AzureADMyOrg": "My org only",
        "AzureADMultipleOrgs": "Multiple orgs",
        "AzureADAndPersonalMicrosoftAccount": "Org + Personal",
        "PersonalMicrosoftAccount": "Personal only",
    }.get(audience, audience)


templates.env.filters["format_date"] = _format_date
templates.env.filters["days_label"] = _days_label
templates.env.filters["risk_badge"] = _risk_badge
templates.env.filters["audience_label"] = _audience_label
