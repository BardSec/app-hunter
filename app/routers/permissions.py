from fastapi import APIRouter, Depends, Request
from app.templates_config import templates
from fastapi.responses import HTMLResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.graph.schemas import PermissionType, RiskLevel
from app.services import app_inventory

router = APIRouter()



@router.get("/", response_class=HTMLResponse)
async def permissions_view(
    request: Request,
    risk: str = "",
    ptype: str = "",
    q: str = "",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_apps = await app_inventory.get_apps(user["access_token"], db)

    # Build a flat list of (app, permission) pairs for display
    rows = []
    for app in all_apps:
        for perm in app.permissions:
            if risk and perm.risk_level != RiskLevel(risk):
                continue
            if ptype and perm.permission_type != PermissionType(ptype):
                continue
            if q and q.lower() not in perm.name.lower() and q.lower() not in app.display_name.lower():
                continue
            rows.append({"app": app, "perm": perm})

    # Sort by risk level descending
    risk_order = {RiskLevel.HIGH: 0, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 2, RiskLevel.NONE: 3}
    rows.sort(key=lambda r: risk_order.get(r["perm"].risk_level, 99))

    return templates.TemplateResponse(
        "permissions/index.html",
        {
            "request": request,
            "current_user": user,
            "mock_mode": settings.MOCK_DATA,
            "active_page": "permissions",
            "rows": rows,
            "filters": {"risk": risk, "ptype": ptype, "q": q},
            "total": len(rows),
        },
    )
