"""
FERPA / COPPA compliance risk scoring.

An app is included in the compliance view if it has at least one FERPA-relevant
permission OR has the offline_access scope.

Scoring:
  +3 per HIGH-risk FERPA permission
  +2 per MEDIUM-risk FERPA permission
  +1 for offline_access
  +2 for no assigned owner
  +2 for external-facing sign-in audience
  +1 for any expired credential

Risk thresholds:
  >= 8 → HIGH
   4–7 → MEDIUM
   1–3 → LOW
"""

from app.graph.schemas import EntraApp, RiskLevel

_EXTERNAL_AUDIENCES = {
    "AzureADMultipleOrgs",
    "AzureADAndPersonalMicrosoftAccount",
    "PersonalMicrosoftAccount",
}


def compute_ferpa_risk(app: EntraApp) -> tuple[int, list[str]]:
    score = 0
    factors: list[str] = []

    for perm in app.permissions:
        if perm.is_ferpa_relevant:
            if perm.risk_level == RiskLevel.HIGH:
                score += 3
                factors.append(f"High-risk FERPA permission: {perm.name} ({perm.permission_type})")
            elif perm.risk_level == RiskLevel.MEDIUM:
                score += 2
                factors.append(f"FERPA-relevant permission: {perm.name} ({perm.permission_type})")

    if app.has_offline_access:
        score += 1
        factors.append("Has offline_access scope (persistent delegated access)")

    if app.is_ownerless:
        score += 2
        factors.append("No assigned owner — governance gap")

    if app.sign_in_audience in _EXTERNAL_AUDIENCES:
        score += 2
        factors.append(f"External-facing sign-in audience: {app.sign_in_audience}")

    if app.has_expired_credentials:
        score += 1
        factors.append("Has expired credentials")

    return score, factors


def ferpa_risk_level(score: int) -> RiskLevel:
    if score >= 8:
        return RiskLevel.HIGH
    if score >= 4:
        return RiskLevel.MEDIUM
    if score >= 1:
        return RiskLevel.LOW
    return RiskLevel.NONE


def is_ferpa_relevant(app: EntraApp) -> bool:
    return (
        any(p.is_ferpa_relevant for p in app.permissions)
        or app.has_offline_access
    )


def enrich_compliance(app: EntraApp) -> EntraApp:
    """Compute FERPA risk score and factors, set is_external_facing."""
    is_external = app.sign_in_audience in _EXTERNAL_AUDIENCES
    score, factors = compute_ferpa_risk(app)
    return app.model_copy(update={
        "ferpa_risk_score": score,
        "ferpa_risk_factors": factors,
        "is_external_facing": is_external,
    })
