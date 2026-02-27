"""
Credential expiry analysis.

Classifies each credential's status and derives top-level has_expired / has_expiring
flags for the app.
"""

from app.graph.schemas import AppCredential, CredentialStatus, EntraApp

EXPIRY_BUCKETS = (
    CredentialStatus.EXPIRED,
    CredentialStatus.EXPIRING_SOON,
    CredentialStatus.EXPIRING,
    CredentialStatus.EXPIRING_LATER,
)


def worst_credential_status(credentials: list[AppCredential]) -> CredentialStatus:
    """Return the most severe credential status across all credentials."""
    if not credentials:
        return CredentialStatus.OK
    order = [
        CredentialStatus.EXPIRED,
        CredentialStatus.EXPIRING_SOON,
        CredentialStatus.EXPIRING,
        CredentialStatus.EXPIRING_LATER,
        CredentialStatus.OK,
    ]
    for status in order:
        if any(c.status == status for c in credentials):
            return status
    return CredentialStatus.OK


def enrich_credentials(app: EntraApp) -> EntraApp:
    """Set has_expired_credentials and has_expiring_credentials on the app."""
    creds = app.credentials
    has_expired = any(c.status == CredentialStatus.EXPIRED for c in creds)
    has_expiring = any(
        c.status in (
            CredentialStatus.EXPIRING_SOON,
            CredentialStatus.EXPIRING,
            CredentialStatus.EXPIRING_LATER,
        )
        for c in creds
    )
    return app.model_copy(update={
        "has_expired_credentials": has_expired,
        "has_expiring_credentials": has_expiring,
    })


def credential_status_label(status: CredentialStatus) -> str:
    labels = {
        CredentialStatus.EXPIRED: "Expired",
        CredentialStatus.EXPIRING_SOON: "Expiring soon",
        CredentialStatus.EXPIRING: "Expiring",
        CredentialStatus.EXPIRING_LATER: "Expiring later",
        CredentialStatus.OK: "OK",
    }
    return labels.get(status, status)


def credential_status_css(status: CredentialStatus) -> str:
    css = {
        CredentialStatus.EXPIRED: "cred-expired",
        CredentialStatus.EXPIRING_SOON: "cred-expiring-soon",
        CredentialStatus.EXPIRING: "cred-expiring",
        CredentialStatus.EXPIRING_LATER: "cred-expiring-late",
        CredentialStatus.OK: "cred-ok",
    }
    return css.get(status, "")
