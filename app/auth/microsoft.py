"""
Microsoft Entra ID OAuth2 helpers using MSAL.

Scopes requested (delegated):
  - https://graph.microsoft.com/Application.Read.All
  - https://graph.microsoft.com/Directory.Read.All
  - https://graph.microsoft.com/User.Read
"""

import msal

from app.config import settings

GRAPH_SCOPES = [
    "https://graph.microsoft.com/Application.Read.All",
    "https://graph.microsoft.com/Directory.Read.All",
    "https://graph.microsoft.com/User.Read",
]


def _msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        client_credential=settings.AZURE_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
    )


def get_auth_url(state: str) -> str:
    """Return the Microsoft login URL to redirect the user to."""
    return _msal_app().get_authorization_request_url(
        scopes=GRAPH_SCOPES,
        state=state,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )


def exchange_code(code: str) -> dict:
    """
    Exchange an authorisation code for tokens.

    Returns the MSAL result dict which contains:
      access_token, id_token, account, error, error_description
    """
    return _msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=GRAPH_SCOPES,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )


def get_logout_url(post_logout_redirect: str = "http://localhost:33333/") -> str:
    return (
        f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}"
        f"/oauth2/v2.0/logout?post_logout_redirect_uri={post_logout_redirect}"
    )
