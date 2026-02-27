from fastapi import APIRouter, Depends, Request
from app.templates_config import templates
from fastapi.responses import HTMLResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.graph.schemas import CredentialStatus
from app.services import app_inventory

router = APIRouter()


_BUCKET_ORDER = [
    CredentialStatus.EXPIRED,
    CredentialStatus.EXPIRING_SOON,
    CredentialStatus.EXPIRING,
    CredentialStatus.EXPIRING_LATER,
    CredentialStatus.OK,
]

_BUCKET_LABELS = {
    CredentialStatus.EXPIRED: "Expired",
    CredentialStatus.EXPIRING_SOON: "Expiring within 30 days",
    CredentialStatus.EXPIRING: "Expiring within 31–60 days",
    CredentialStatus.EXPIRING_LATER: "Expiring within 61–90 days",
    CredentialStatus.OK: "Healthy (> 90 days)",
}

_BUCKET_CSS = {
    CredentialStatus.EXPIRED: "border-red-400 bg-red-50",
    CredentialStatus.EXPIRING_SOON: "border-orange-400 bg-orange-50",
    CredentialStatus.EXPIRING: "border-amber-400 bg-amber-50",
    CredentialStatus.EXPIRING_LATER: "border-yellow-400 bg-yellow-50",
    CredentialStatus.OK: "border-green-400 bg-green-50",
}


@router.get("/", response_class=HTMLResponse)
async def credentials_view(
    request: Request,
    ctype: str = "",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_apps = await app_inventory.get_apps(user["access_token"], db)

    # Build flat rows: (app, credential)
    all_rows = []
    for app in all_apps:
        for cred in app.credentials:
            if ctype and cred.credential_type != ctype:
                continue
            all_rows.append({"app": app, "cred": cred})

    # Group into buckets
    buckets = {}
    for status in _BUCKET_ORDER:
        bucket_rows = [r for r in all_rows if r["cred"].status == status]
        if bucket_rows:
            buckets[status] = {
                "label": _BUCKET_LABELS[status],
                "css": _BUCKET_CSS[status],
                "rows": bucket_rows,
            }

    return templates.TemplateResponse(
        "credentials/index.html",
        {
            "request": request,
            "current_user": user,
            "mock_mode": settings.MOCK_DATA,
            "active_page": "credentials",
            "buckets": buckets,
            "bucket_order": [s for s in _BUCKET_ORDER if s in buckets],
            "total": len(all_rows),
            "filters": {"ctype": ctype},
            "CredentialStatus": CredentialStatus,
        },
    )
