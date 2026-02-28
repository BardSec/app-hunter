from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PermissionType(str, Enum):
    APPLICATION = "application"
    DELEGATED = "delegated"


class RiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class CredentialStatus(str, Enum):
    EXPIRED = "EXPIRED"
    EXPIRING_SOON = "EXPIRING_SOON"    # 0–30 days
    EXPIRING = "EXPIRING"              # 31–60 days
    EXPIRING_LATER = "EXPIRING_LATER"  # 61–90 days
    OK = "OK"


class AppPermission(BaseModel):
    id: str
    name: str
    description: str = ""
    permission_type: PermissionType
    risk_level: RiskLevel = RiskLevel.NONE
    is_ferpa_relevant: bool = False
    is_offline_access: bool = False
    resource_app_id: str = "00000003-0000-0000-c000-000000000000"


class AppCredential(BaseModel):
    key_id: str
    display_name: str
    credential_type: str   # "secret" | "certificate" | "federation"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: CredentialStatus = CredentialStatus.OK
    days_until_expiry: Optional[int] = None


class AppOwner(BaseModel):
    id: str
    display_name: str
    user_principal_name: Optional[str] = None


class AppRoleAssignment(BaseModel):
    id: str
    principal_display_name: str
    principal_type: str  # "User", "Group", or "ServicePrincipal"
    app_role_id: str = "00000000-0000-0000-0000-000000000000"


class EntraApp(BaseModel):
    # Raw Graph fields
    id: str
    app_id: str
    display_name: str
    created_date: Optional[datetime] = None
    sign_in_audience: str = "AzureADMyOrg"
    publisher_domain: Optional[str] = None
    description: Optional[str] = None
    owners: list[AppOwner] = []
    permissions: list[AppPermission] = []
    credentials: list[AppCredential] = []

    # Service principal / enterprise app fields
    assignment_required: bool = False
    app_role_assignments: list[AppRoleAssignment] = []

    # Computed / enriched fields (populated by the service layer)
    risk_level: RiskLevel = RiskLevel.NONE
    is_ownerless: bool = False
    has_expired_credentials: bool = False
    has_expiring_credentials: bool = False   # within 90 days
    has_high_risk_permissions: bool = False
    ferpa_risk_score: int = 0
    ferpa_risk_factors: list[str] = []
    has_offline_access: bool = False
    is_external_facing: bool = False         # audience != AzureADMyOrg


class TenantInfo(BaseModel):
    tenant_id: str
    tenant_name: str
    display_name: str
