"""
App inventory service.

Calls the Graph client, then runs each app through the enrichment pipeline:
  1. permission_audit   → classify permission risk levels
  2. credential_scan   → classify credential expiry
  3. compliance        → compute FERPA risk score + is_external_facing
  4. derive is_ownerless

Also saves an AuditSnapshot to SQLite after each fetch.
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.client import GraphClient
from app.graph.schemas import EntraApp, RiskLevel, TenantInfo

_RISK_ORDER = {RiskLevel.NONE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}
from app.models.audit import AuditSnapshot
from app.services import compliance as compliance_svc
from app.services import credential_scan, permission_audit


def _enrich(app: EntraApp) -> EntraApp:
    app = permission_audit.enrich_permissions(app)
    app = credential_scan.enrich_credentials(app)
    app = compliance_svc.enrich_compliance(app)
    app = app.model_copy(update={"is_ownerless": len(app.owners) == 0})
    return app


async def get_apps(
    access_token: str,
    db: AsyncSession,
    *,
    q: str = "",
    risk: str = "",
    has_owner: str = "",
    audience: str = "",
    sort_by: str = "",
    sort_dir: str = "asc",
) -> list[EntraApp]:
    client = GraphClient(access_token)
    raw = await client.get_app_registrations()
    enriched = [_enrich(a) for a in raw]

    # Save snapshot
    tenant = await client.get_tenant_info()
    await _save_snapshot(db, enriched, tenant)

    filtered = _filter(enriched, q=q, risk=risk, has_owner=has_owner, audience=audience)
    return _sort(filtered, sort_by, sort_dir)


async def get_app_detail(access_token: str, app_id: str) -> EntraApp | None:
    client = GraphClient(access_token)
    raw = await client.get_app_by_id(app_id)
    if raw is None:
        return None
    return _enrich(raw)


async def get_tenant_info(access_token: str) -> TenantInfo:
    return await GraphClient(access_token).get_tenant_info()


def _filter(
    apps: list[EntraApp],
    *,
    q: str,
    risk: str,
    has_owner: str,
    audience: str,
) -> list[EntraApp]:
    result = apps

    if q:
        ql = q.lower()
        result = [a for a in result if ql in a.display_name.lower()]

    if risk:
        result = [a for a in result if a.risk_level == RiskLevel(risk)]

    if has_owner == "yes":
        result = [a for a in result if not a.is_ownerless]
    elif has_owner == "no":
        result = [a for a in result if a.is_ownerless]

    if audience:
        result = [a for a in result if a.sign_in_audience == audience]

    return result


def _sort(apps: list[EntraApp], sort_by: str, sort_dir: str) -> list[EntraApp]:
    if not sort_by:
        return apps
    reverse = sort_dir == "desc"
    if sort_by == "created":
        return sorted(apps, key=lambda a: a.created_date or datetime.min, reverse=reverse)
    if sort_by == "audience":
        return sorted(apps, key=lambda a: a.sign_in_audience, reverse=reverse)
    if sort_by == "owner":
        return sorted(
            apps,
            key=lambda a: (1, "") if not a.owners else (0, a.owners[0].display_name.lower()),
            reverse=reverse,
        )
    if sort_by == "risk":
        return sorted(apps, key=lambda a: _RISK_ORDER[a.risk_level], reverse=reverse)
    return apps


async def _save_snapshot(
    db: AsyncSession,
    apps: list[EntraApp],
    tenant: TenantInfo,
) -> None:
    from app.graph.schemas import CredentialStatus

    expired = sum(1 for a in apps if a.has_expired_credentials)
    exp_30 = sum(
        1 for a in apps
        if any(c.status == CredentialStatus.EXPIRING_SOON for c in a.credentials)
    )
    exp_60 = sum(
        1 for a in apps
        if any(c.status == CredentialStatus.EXPIRING for c in a.credentials)
    )
    exp_90 = sum(
        1 for a in apps
        if any(c.status == CredentialStatus.EXPIRING_LATER for c in a.credentials)
    )
    ferpa_count = sum(1 for a in apps if compliance_svc.is_ferpa_relevant(a))

    snapshot = AuditSnapshot(
        created_at=datetime.utcnow(),
        tenant_id=tenant.tenant_id,
        tenant_name=tenant.tenant_name,
        total_apps=len(apps),
        high_risk_count=sum(1 for a in apps if a.risk_level == RiskLevel.HIGH),
        ownerless_count=sum(1 for a in apps if a.is_ownerless),
        expired_cred_count=expired,
        expiring_30_count=exp_30,
        expiring_60_count=exp_60,
        expiring_90_count=exp_90,
        ferpa_flagged_count=ferpa_count,
    )
    try:
        db.add(snapshot)
        await db.commit()
    except Exception:
        await db.rollback()
