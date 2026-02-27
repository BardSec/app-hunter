"""
Permission risk classification.

Classifies each AppPermission's risk_level and ferpa/offline flags, then
derives the top-level risk_level for the whole app.
"""

from app.graph.schemas import AppPermission, EntraApp, PermissionType, RiskLevel

# ── Risk buckets ───────────────────────────────────────────────────────────────

HIGH_RISK_PERMS: set[str] = {
    "Directory.ReadWrite.All",
    "User.ReadWrite.All",
    "RoleManagement.ReadWrite.Directory",
    "Application.ReadWrite.All",
    "GroupMember.ReadWrite.All",
    "Sites.FullControl.All",
    "Mail.ReadWrite",
    "Files.ReadWrite.All",
    "Sites.ReadWrite.All",
    "DeviceManagementApps.ReadWrite.All",
}

MEDIUM_RISK_PERMS: set[str] = {
    "Directory.Read.All",
    "User.Read.All",
    "Sites.Read.All",
    "Files.Read.All",
    "Mail.Read",
    "Group.ReadWrite.All",
    "GroupMember.Read.All",
}

# Permissions flagged for FERPA / COPPA review (as specified by the admin)
FERPA_PERMS: set[str] = {
    "Directory.Read.All",
    "Directory.ReadWrite.All",
    "User.Read.All",
    "User.ReadWrite.All",
    "Sites.Read.All",
    "Sites.ReadWrite.All",
    "Sites.FullControl.All",
    "Files.Read.All",
    "Files.ReadWrite.All",
    "Mail.Read",
    "Mail.ReadWrite",
}

OFFLINE_ACCESS_NAME = "offline_access"


# ── Public helpers ─────────────────────────────────────────────────────────────

def classify_permission(perm: AppPermission) -> AppPermission:
    """Return a copy of *perm* with risk_level, is_ferpa_relevant and is_offline_access set."""
    name = perm.name
    risk = RiskLevel.NONE

    if name in HIGH_RISK_PERMS:
        risk = RiskLevel.HIGH
    elif name in MEDIUM_RISK_PERMS:
        risk = RiskLevel.MEDIUM
    elif name not in ("openid", "profile", "email", "User.Read", "offline_access"):
        risk = RiskLevel.LOW

    return perm.model_copy(update={
        "risk_level": risk,
        "is_ferpa_relevant": name in FERPA_PERMS,
        "is_offline_access": name == OFFLINE_ACCESS_NAME,
    })


def app_risk_level(app: EntraApp) -> RiskLevel:
    """Derive the top-level risk level from the app's classified permissions."""
    levels = [p.risk_level for p in app.permissions]
    if RiskLevel.HIGH in levels:
        return RiskLevel.HIGH
    if RiskLevel.MEDIUM in levels:
        return RiskLevel.MEDIUM
    if RiskLevel.LOW in levels:
        return RiskLevel.LOW
    return RiskLevel.NONE


def enrich_permissions(app: EntraApp) -> EntraApp:
    """
    Classify every permission on the app and set top-level risk flags.
    Returns a new EntraApp (Pydantic model_copy).
    """
    classified = [classify_permission(p) for p in app.permissions]
    risk = app_risk_level(app.model_copy(update={"permissions": classified}))
    has_high = any(p.risk_level == RiskLevel.HIGH for p in classified)
    has_offline = any(p.is_offline_access for p in classified)

    return app.model_copy(update={
        "permissions": classified,
        "risk_level": risk,
        "has_high_risk_permissions": has_high,
        "has_offline_access": has_offline,
    })
