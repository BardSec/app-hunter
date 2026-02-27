from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditSnapshot(Base):
    """Point-in-time summary stored automatically each time an audit runs."""

    __tablename__ = "audit_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tenant_id: Mapped[str] = mapped_column(String(256))
    tenant_name: Mapped[str] = mapped_column(String(256))
    total_apps: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    ownerless_count: Mapped[int] = mapped_column(Integer, default=0)
    expired_cred_count: Mapped[int] = mapped_column(Integer, default=0)
    expiring_30_count: Mapped[int] = mapped_column(Integer, default=0)
    expiring_60_count: Mapped[int] = mapped_column(Integer, default=0)
    expiring_90_count: Mapped[int] = mapped_column(Integer, default=0)
    ferpa_flagged_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ComplianceNote(Base):
    """Admin notes attached to apps in the compliance view."""

    __tablename__ = "compliance_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_id: Mapped[str] = mapped_column(String(256), index=True)
    app_display_name: Mapped[str] = mapped_column(String(512))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[str] = mapped_column(String(256))
