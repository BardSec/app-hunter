from fastapi import APIRouter, Depends, Request
from app.templates_config import templates

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.services import app_inventory, compliance as compliance_svc

router = APIRouter()



@router.get("/")
async def dashboard(
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    apps = await app_inventory.get_apps(user["access_token"], db)
    tenant = await app_inventory.get_tenant_info(user["access_token"])

    from app.graph.schemas import CredentialStatus, RiskLevel

    expired_apps = [
        a for a in apps
        if any(c.status == CredentialStatus.EXPIRED for c in a.credentials)
    ]
    expiring_soon_apps = [
        a for a in apps
        if any(c.status == CredentialStatus.EXPIRING_SOON for c in a.credentials)
    ]
    ferpa_apps = [a for a in apps if compliance_svc.is_ferpa_relevant(a)]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": user,
            "tenant": tenant,
            "mock_mode": settings.MOCK_DATA,
            "active_page": "dashboard",
            # Summary counts
            "total_apps": len(apps),
            "high_risk_count": sum(1 for a in apps if a.risk_level == RiskLevel.HIGH),
            "ownerless_count": sum(1 for a in apps if a.is_ownerless),
            "expired_cred_count": len(expired_apps),
            "expiring_soon_count": len(expiring_soon_apps),
            "ferpa_count": len(ferpa_apps),
            # Quick-view lists
            "expired_apps": expired_apps[:5],
            "ownerless_apps": [a for a in apps if a.is_ownerless][:5],
            "high_risk_apps": [a for a in apps if a.risk_level == RiskLevel.HIGH][:5],
        },
    )
