import secrets

from fastapi import APIRouter, Request
from app.templates_config import templates
from fastapi.responses import RedirectResponse


from app.auth import microsoft
from app.config import settings

router = APIRouter()



@router.get("/login")
async def login(request: Request):
    if settings.MOCK_DATA:
        # In mock mode skip OAuth and go straight to the dashboard
        return RedirectResponse(url="/", status_code=302)

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    auth_url = microsoft.get_auth_url(state)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if settings.MOCK_DATA:
        return RedirectResponse(url="/", status_code=302)

    # If a session already exists, skip the exchange. This protects against
    # the callback being hit twice (browser back/forward, history reload,
    # link prefetching, or a duplicate tab) — the second redemption would
    # otherwise fail with AADSTS54005 (code already redeemed).
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)

    if error:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Microsoft login error: {error}", "mock_mode": False},
        )

    saved_state = request.session.pop("oauth_state", None)
    if state != saved_state:
        # State already consumed by a parallel callback that completed first.
        if request.session.get("user"):
            return RedirectResponse(url="/", status_code=302)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid state parameter.", "mock_mode": False},
        )

    result = microsoft.exchange_code(code)
    if "error" in result:
        # If a concurrent callback beat us to the redemption, the user is
        # already authenticated — silently send them home.
        if request.session.get("user"):
            return RedirectResponse(url="/", status_code=302)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": result.get("error_description", result["error"]),
                "mock_mode": False,
            },
        )

    account = result.get("id_token_claims", {})
    request.session["user"] = {
        "id": account.get("oid", ""),
        "name": account.get("name", ""),
        "username": account.get("preferred_username", ""),
        "tenant_id": account.get("tid", ""),
        "tenant_name": account.get("tenant_display_name", ""),
        "access_token": result["access_token"],
    }
    return RedirectResponse(url="/", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    if settings.MOCK_DATA:
        return RedirectResponse(url="/auth/login", status_code=302)
    return RedirectResponse(url=microsoft.get_logout_url(), status_code=302)
