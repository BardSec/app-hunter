"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("tenant_id", sa.String(256), nullable=True),
        sa.Column("tenant_name", sa.String(256), nullable=True),
        sa.Column("total_apps", sa.Integer(), nullable=True),
        sa.Column("high_risk_count", sa.Integer(), nullable=True),
        sa.Column("ownerless_count", sa.Integer(), nullable=True),
        sa.Column("expired_cred_count", sa.Integer(), nullable=True),
        sa.Column("expiring_30_count", sa.Integer(), nullable=True),
        sa.Column("expiring_60_count", sa.Integer(), nullable=True),
        sa.Column("expiring_90_count", sa.Integer(), nullable=True),
        sa.Column("ferpa_flagged_count", sa.Integer(), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_snapshots_id", "audit_snapshots", ["id"])

    op.create_table(
        "compliance_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("app_id", sa.String(256), nullable=True),
        sa.Column("app_display_name", sa.String(512), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_notes_id", "compliance_notes", ["id"])
    op.create_index("ix_compliance_notes_app_id", "compliance_notes", ["app_id"])


def downgrade() -> None:
    op.drop_index("ix_compliance_notes_app_id", table_name="compliance_notes")
    op.drop_index("ix_compliance_notes_id", table_name="compliance_notes")
    op.drop_table("compliance_notes")
    op.drop_index("ix_audit_snapshots_id", table_name="audit_snapshots")
    op.drop_table("audit_snapshots")
