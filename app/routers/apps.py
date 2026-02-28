import csv
import io

from fastapi import APIRouter, Depends, Request
from app.templates_config import templates
from fastapi.responses import HTMLResponse, StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.services import app_inventory

router = APIRouter()



@router.get("/", response_class=HTMLResponse)
async def app_list(
    request: Request,
    q: str = "",
    risk: str = "",
    has_owner: str = "",
    audience: str = "",
    sort_by: str = "",
    sort_dir: str = "asc",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    apps = await app_inventory.get_apps(
        user["access_token"], db,
        q=q, risk=risk, has_owner=has_owner, audience=audience,
        sort_by=sort_by, sort_dir=sort_dir,
    )

    context = {
        "request": request,
        "current_user": user,
        "mock_mode": settings.MOCK_DATA,
        "active_page": "apps",
        "apps": apps,
        "filters": {"q": q, "risk": risk, "has_owner": has_owner, "audience": audience},
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "total": len(apps),
    }

    # HTMX partial — return only the table rows fragment
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("apps/_table_rows.html", context)

    return templates.TemplateResponse("apps/index.html", context)


@router.get("/export")
async def export_apps_csv(
    q: str = "",
    risk: str = "",
    has_owner: str = "",
    audience: str = "",
    sort_by: str = "",
    sort_dir: str = "asc",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    apps = await app_inventory.get_apps(
        user["access_token"], db,
        q=q, risk=risk, has_owner=has_owner, audience=audience,
        sort_by=sort_by, sort_dir=sort_dir,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "App Name", "Client ID", "Object ID", "Created", "Audience",
        "Owner(s)", "Risk Level", "Assignment Required", "Assigned Principals",
        "Top Permission", "Credential Status", "FERPA Score",
    ])

    for app in apps:
        owners = " | ".join(o.display_name for o in app.owners)
        principals = " | ".join(
            f"{a.principal_display_name} ({a.principal_type})"
            for a in app.app_role_assignments
        )
        high = [p for p in app.permissions if p.risk_level == "HIGH"]
        med  = [p for p in app.permissions if p.risk_level == "MEDIUM"]
        top_perm = high[0].name if high else (med[0].name if med else "")
        if app.has_expired_credentials:
            cred_status = "Expired"
        elif app.has_expiring_credentials:
            cred_status = "Expiring Soon"
        elif app.credentials:
            cred_status = "OK"
        else:
            cred_status = "None"

        writer.writerow([
            app.display_name,
            app.app_id,
            app.id,
            app.created_date.strftime("%Y-%m-%d") if app.created_date else "",
            app.sign_in_audience,
            owners,
            app.risk_level,
            "Yes" if app.assignment_required else "No",
            principals,
            top_perm,
            cred_status,
            app.ferpa_risk_score,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=app-inventory.csv"},
    )


@router.get("/{app_id}", response_class=HTMLResponse)
async def app_detail(
    app_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    app = await app_inventory.get_app_detail(user["access_token"], app_id)
    if app is None:
        return HTMLResponse("<p>App not found.</p>", status_code=404)

    return templates.TemplateResponse(
        "apps/detail.html",
        {
            "request": request,
            "current_user": user,
            "mock_mode": settings.MOCK_DATA,
            "active_page": "apps",
            "app": app,
        },
    )
