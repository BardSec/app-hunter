from fastapi import APIRouter, Depends, Form, Request
from app.templates_config import templates
from fastapi.responses import HTMLResponse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.graph.schemas import RiskLevel
from app.models.audit import ComplianceNote
from app.services import app_inventory
from app.services.compliance import ferpa_risk_level, is_ferpa_relevant

router = APIRouter()



@router.get("/", response_class=HTMLResponse)
async def compliance_view(
    request: Request,
    risk: str = "",
    q: str = "",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_apps = await app_inventory.get_apps(user["access_token"], db)

    # Only FERPA-relevant apps
    ferpa_apps = [a for a in all_apps if is_ferpa_relevant(a)]

    # Apply filters
    if risk:
        ferpa_apps = [a for a in ferpa_apps if ferpa_risk_level(a.ferpa_risk_score) == RiskLevel(risk)]
    if q:
        ql = q.lower()
        ferpa_apps = [a for a in ferpa_apps if ql in a.display_name.lower()]

    # Sort by FERPA risk score descending
    ferpa_apps.sort(key=lambda a: a.ferpa_risk_score, reverse=True)

    # Load compliance notes for these apps
    app_ids = [a.id for a in ferpa_apps]
    notes_result = await db.execute(
        select(ComplianceNote).where(ComplianceNote.app_id.in_(app_ids))
    )
    notes_by_app: dict[str, ComplianceNote] = {
        n.app_id: n for n in notes_result.scalars().all()
    }

    return templates.TemplateResponse(
        "compliance/index.html",
        {
            "request": request,
            "current_user": user,
            "mock_mode": settings.MOCK_DATA,
            "active_page": "compliance",
            "apps": ferpa_apps,
            "notes_by_app": notes_by_app,
            "filters": {"risk": risk, "q": q},
            "total": len(ferpa_apps),
            "ferpa_risk_level": ferpa_risk_level,
        },
    )


@router.post("/{app_id}/note", response_class=HTMLResponse)
async def save_note(
    app_id: str,
    request: Request,
    note_text: str = Form(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save or update a compliance note for an app (HTMX target)."""
    # Look for existing note
    result = await db.execute(
        select(ComplianceNote).where(ComplianceNote.app_id == app_id)
    )
    existing = result.scalar_one_or_none()

    app = await app_inventory.get_app_detail(user["access_token"], app_id)
    app_name = app.display_name if app else app_id

    if existing:
        existing.note = note_text
        existing.updated_at = __import__("datetime").datetime.utcnow()
    else:
        db.add(ComplianceNote(
            app_id=app_id,
            app_display_name=app_name,
            note=note_text,
            created_by=user.get("username", ""),
        ))

    await db.commit()

    # Return updated note snippet for HTMX swap
    return HTMLResponse(
        f'<p class="text-sm text-gray-700 mt-1">{note_text}</p>'
        f'<button class="btn btn-xs btn-ghost mt-1" '
        f'hx-get="/compliance/{app_id}/note-form" hx-target="#note-{app_id}" hx-swap="outerHTML">'
        f'Edit</button>'
    )


@router.get("/{app_id}/note-form", response_class=HTMLResponse)
async def note_form(
    app_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ComplianceNote).where(ComplianceNote.app_id == app_id)
    )
    existing = result.scalar_one_or_none()
    current_note = existing.note if existing else ""

    return HTMLResponse(f"""
    <div id="note-{app_id}">
      <form hx-post="/compliance/{app_id}/note"
            hx-target="#note-{app_id}"
            hx-swap="outerHTML"
            class="flex gap-2 mt-1">
        <textarea name="note_text" rows="2"
          class="textarea textarea-bordered textarea-sm flex-1 text-sm"
          placeholder="Add compliance note...">{current_note}</textarea>
        <button type="submit" class="btn btn-sm btn-primary">Save</button>
      </form>
    </div>
    """)
