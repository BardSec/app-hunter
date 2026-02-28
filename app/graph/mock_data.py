"""
Realistic mock data for a fictitious K-12 district: Riverside Unified School District.

All credential expiry dates are computed relative to runtime so the demo always
shows a realistic spread of expired / expiring-soon / healthy credentials.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.graph.schemas import (
    AppCredential,
    AppOwner,
    AppPermission,
    AppRoleAssignment,
    CredentialStatus,
    EntraApp,
    PermissionType,
    RiskLevel,
    TenantInfo,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt(days_offset: int) -> datetime:
    """Return a naive UTC datetime offset from now."""
    return _now() + timedelta(days=days_offset)


def _credential_status(end_date: Optional[datetime]) -> tuple[CredentialStatus, Optional[int]]:
    if end_date is None:
        return CredentialStatus.OK, None
    delta = (end_date - _now()).days
    if delta < 0:
        return CredentialStatus.EXPIRED, delta
    if delta <= 30:
        return CredentialStatus.EXPIRING_SOON, delta
    if delta <= 60:
        return CredentialStatus.EXPIRING, delta
    if delta <= 90:
        return CredentialStatus.EXPIRING_LATER, delta
    return CredentialStatus.OK, delta


def _secret(key_id: str, name: str, days: int) -> AppCredential:
    end = _dt(days)
    status, remaining = _credential_status(end)
    return AppCredential(
        key_id=key_id,
        display_name=name,
        credential_type="secret",
        start_date=_dt(days - 365),
        end_date=end,
        status=status,
        days_until_expiry=remaining,
    )


def _cert(key_id: str, name: str, days: int) -> AppCredential:
    end = _dt(days)
    status, remaining = _credential_status(end)
    return AppCredential(
        key_id=key_id,
        display_name=name,
        credential_type="certificate",
        start_date=_dt(days - 730),
        end_date=end,
        status=status,
        days_until_expiry=remaining,
    )


def _fed(key_id: str, name: str, days: int) -> AppCredential:
    end = _dt(days)
    status, remaining = _credential_status(end)
    return AppCredential(
        key_id=key_id,
        display_name=name,
        credential_type="federation",
        start_date=_dt(days - 365),
        end_date=end,
        status=status,
        days_until_expiry=remaining,
    )


def _assignment(aid: str, name: str, ptype: str) -> AppRoleAssignment:
    return AppRoleAssignment(id=aid, principal_display_name=name, principal_type=ptype)


def _owner(uid: str, name: str, upn: str) -> AppOwner:
    return AppOwner(id=uid, display_name=name, user_principal_name=upn)


def _perm(
    pid: str,
    name: str,
    ptype: PermissionType,
    risk: RiskLevel,
    ferpa: bool = False,
    offline: bool = False,
    desc: str = "",
) -> AppPermission:
    return AppPermission(
        id=pid,
        name=name,
        description=desc,
        permission_type=ptype,
        risk_level=risk,
        is_ferpa_relevant=ferpa,
        is_offline_access=offline,
    )


# ── permission constants ───────────────────────────────────────────────────────

APP  = PermissionType.APPLICATION
DEL  = PermissionType.DELEGATED
H    = RiskLevel.HIGH
M    = RiskLevel.MEDIUM
L    = RiskLevel.LOW

# ── owners ─────────────────────────────────────────────────────────────────────

IT_ADMIN   = _owner("owner-001", "James Smith",    "jsmith@riverside-usd.edu")
HR_DIR     = _owner("owner-002", "Maria Wilson",   "mwilson@riverside-usd.edu")
CURR_DIR   = _owner("owner-003", "Angela Brown",   "abrown@riverside-usd.edu")
LIB_COORD  = _owner("owner-004", "Thanh Nguyen",   "tnguyen@riverside-usd.edu")

# ── apps ───────────────────────────────────────────────────────────────────────

def _build_apps() -> list[EntraApp]:
    return [
        # ── 1. SIS Integration – PowerSchool ─────────────────────────────────
        EntraApp(
            id="app-001",
            app_id="aaaaaaaa-0001-0001-0001-aaaaaaaaaaaa",
            display_name="SIS Integration – PowerSchool",
            created_date=datetime(2021, 3, 15),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Student Information System integration for roster sync.",
            owners=[],
            permissions=[
                _perm("p-001a", "User.ReadWrite.All", APP, H, ferpa=True,
                      desc="Read and write all users' full profiles"),
                _perm("p-001b", "Directory.Read.All", APP, H, ferpa=True,
                      desc="Read directory data"),
                _perm("p-001c", "Mail.Read", APP, M, ferpa=True,
                      desc="Read mail in all mailboxes"),
            ],
            credentials=[
                _secret("cred-001a", "SIS Primary Secret", -60),   # EXPIRED
            ],
            # Assignment required but no principals assigned — governance gap
            assignment_required=True,
            app_role_assignments=[],
        ),

        # ── 2. Canvas LMS ─────────────────────────────────────────────────────
        EntraApp(
            id="app-002",
            app_id="bbbbbbbb-0002-0002-0002-bbbbbbbbbbbb",
            display_name="Canvas LMS",
            created_date=datetime(2020, 9, 1),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Learning Management System used district-wide.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-002a", "Files.ReadWrite.All", DEL, H, ferpa=True,
                      desc="Have full access to all files user can access"),
                _perm("p-002b", "Sites.Read.All", DEL, M, ferpa=True,
                      desc="Read items in all site collections"),
                _perm("p-002c", "User.Read", DEL, L,
                      desc="Sign in and read user profile"),
                _perm("p-002d", "offline_access", DEL, L, offline=True,
                      desc="Maintain access to data you have given it access to"),
            ],
            credentials=[
                _secret("cred-002a", "Canvas Production Secret", 180),
            ],
        ),

        # ── 3. Google Workspace Directory Sync ───────────────────────────────
        EntraApp(
            id="app-003",
            app_id="cccccccc-0003-0003-0003-cccccccccccc",
            display_name="Google Workspace Directory Sync",
            created_date=datetime(2019, 11, 20),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Syncs Entra users to Google Workspace.",
            owners=[],
            permissions=[
                _perm("p-003a", "Directory.ReadWrite.All", APP, H, ferpa=True,
                      desc="Read and write directory data"),
                _perm("p-003b", "User.Read.All", APP, H, ferpa=True,
                      desc="Read all users' full profiles"),
            ],
            credentials=[
                _secret("cred-003a", "GWS Sync Secret", 18),   # EXPIRING_SOON
            ],
        ),

        # ── 4. Clever SSO ────────────────────────────────────────────────────
        EntraApp(
            id="app-004",
            app_id="dddddddd-0004-0004-0004-dddddddddddd",
            display_name="Clever SSO",
            created_date=datetime(2022, 1, 10),
            sign_in_audience="AzureADAndPersonalMicrosoftAccount",
            publisher_domain="riverside-usd.edu",
            description="Single Sign-On integration for Clever EdTech platform.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-004a", "User.Read", DEL, L,
                      desc="Sign in and read user profile"),
                _perm("p-004b", "offline_access", DEL, L, offline=True,
                      desc="Maintain access to data you have given it access to"),
                _perm("p-004c", "openid", DEL, L, desc="Sign users in"),
                _perm("p-004d", "profile", DEL, L, desc="View users' basic profile"),
            ],
            credentials=[
                _secret("cred-004a", "Clever OAuth Secret", 200),
            ],
        ),

        # ── 5. District HR Portal ─────────────────────────────────────────────
        EntraApp(
            id="app-005",
            app_id="eeeeeeee-0005-0005-0005-eeeeeeeeeeee",
            display_name="District HR Portal",
            created_date=datetime(2018, 6, 1),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Internal HR self-service portal for staff.",
            owners=[HR_DIR],
            permissions=[
                _perm("p-005a", "User.ReadWrite.All", APP, H, ferpa=True,
                      desc="Read and write all users' full profiles"),
                _perm("p-005b", "Mail.ReadWrite", APP, H, ferpa=True,
                      desc="Read and write mail in all mailboxes"),
            ],
            credentials=[
                _secret("cred-005a", "HR Portal Secret", 45),   # EXPIRING
            ],
            assignment_required=True,
            app_role_assignments=[
                _assignment("ara-005a", "HR Staff",         "Group"),
                _assignment("ara-005b", "Maria Wilson",     "User"),
                _assignment("ara-005c", "Payroll Services", "Group"),
            ],
        ),

        # ── 6. SubFinder – Substitute Management ─────────────────────────────
        EntraApp(
            id="app-006",
            app_id="ffffffff-0006-0006-0006-ffffffffffff",
            display_name="SubFinder – Substitute Management",
            created_date=datetime(2020, 2, 14),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Manages substitute teacher requests and approvals.",
            owners=[],
            permissions=[
                _perm("p-006a", "Sites.FullControl.All", APP, H, ferpa=True,
                      desc="Have full control of all site collections"),
                _perm("p-006b", "User.Read.All", APP, H, ferpa=True,
                      desc="Read all users' full profiles"),
            ],
            credentials=[
                _cert("cred-006a", "SubFinder Certificate", 25),   # EXPIRING_SOON
                _secret("cred-006b", "SubFinder Backup Secret", 75),  # EXPIRING_LATER
            ],
            assignment_required=True,
            app_role_assignments=[
                _assignment("ara-006a", "Substitute Coordinators", "Group"),
                _assignment("ara-006b", "James Smith",              "User"),
            ],
        ),

        # ── 7. Illuminate – Assessment Platform ──────────────────────────────
        EntraApp(
            id="app-007",
            app_id="11111111-0007-0007-0007-111111111111",
            display_name="Illuminate – Assessment Platform",
            created_date=datetime(2021, 8, 20),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="District assessment and data analytics platform.",
            owners=[CURR_DIR],
            permissions=[
                _perm("p-007a", "User.Read.All", APP, H, ferpa=True,
                      desc="Read all users' full profiles"),
                _perm("p-007b", "Mail.ReadWrite", APP, H, ferpa=True,
                      desc="Read and write mail in all mailboxes"),
            ],
            credentials=[
                _secret("cred-007a", "Illuminate Primary Secret", 150),
            ],
        ),

        # ── 8. Parent Portal ─────────────────────────────────────────────────
        EntraApp(
            id="app-008",
            app_id="22222222-0008-0008-0008-222222222222",
            display_name="Parent Portal",
            created_date=datetime(2022, 3, 5),
            sign_in_audience="AzureADMultipleOrgs",
            publisher_domain="riverside-usd.edu",
            description="Guardian-facing portal for grades and school news.",
            owners=[],
            permissions=[
                _perm("p-008a", "User.Read.All", DEL, H, ferpa=True,
                      desc="Read all users' full profiles"),
                _perm("p-008b", "offline_access", DEL, L, offline=True,
                      desc="Maintain access to data you have given it access to"),
                _perm("p-008c", "openid", DEL, L, desc="Sign users in"),
            ],
            credentials=[
                _secret("cred-008a", "Parent Portal Secret", -30),   # EXPIRED
            ],
        ),

        # ── 9. Diligent – Board Document Management ───────────────────────────
        EntraApp(
            id="app-009",
            app_id="33333333-0009-0009-0009-333333333333",
            display_name="Diligent – Board Document Management",
            created_date=datetime(2019, 4, 22),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Secure document management for board meetings.",
            owners=[],
            permissions=[
                _perm("p-009a", "Sites.ReadWrite.All", APP, H, ferpa=True,
                      desc="Read and write items in all site collections"),
                _perm("p-009b", "Files.ReadWrite.All", APP, H, ferpa=True,
                      desc="Read and write files in all site collections"),
            ],
            credentials=[
                _cert("cred-009a", "Diligent Certificate", -90),   # EXPIRED
            ],
            assignment_required=True,
            app_role_assignments=[
                _assignment("ara-009a", "Board Members",     "Group"),
                _assignment("ara-009b", "Superintendent",    "Group"),
                _assignment("ara-009c", "District Counsel",  "User"),
            ],
        ),

        # ── 10. PLC Collaboration Tool ────────────────────────────────────────
        EntraApp(
            id="app-010",
            app_id="44444444-0010-0010-0010-444444444444",
            display_name="PLC Collaboration Tool",
            created_date=datetime(2023, 1, 15),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Professional Learning Community collaboration workspace.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-010a", "Files.Read.All", DEL, M, ferpa=True,
                      desc="Read all files that user can access"),
                _perm("p-010b", "User.Read", DEL, L,
                      desc="Sign in and read user profile"),
            ],
            credentials=[
                _secret("cred-010a", "PLC Tool Secret", 300),
            ],
        ),

        # ── 11. Destiny – Library Catalog ────────────────────────────────────
        EntraApp(
            id="app-011",
            app_id="55555555-0011-0011-0011-555555555555",
            display_name="Destiny – Library Catalog",
            created_date=datetime(2020, 7, 1),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="District library catalog and circulation system.",
            owners=[LIB_COORD],
            permissions=[
                _perm("p-011a", "User.Read", DEL, L,
                      desc="Sign in and read user profile"),
                _perm("p-011b", "openid", DEL, L, desc="Sign users in"),
                _perm("p-011c", "profile", DEL, L, desc="View users' basic profile"),
            ],
            credentials=[
                _secret("cred-011a", "Destiny Primary Secret", 400),
            ],
        ),

        # ── 12. ServiceNow – IT Help Desk ─────────────────────────────────────
        EntraApp(
            id="app-012",
            app_id="66666666-0012-0012-0012-666666666666",
            display_name="ServiceNow – IT Help Desk",
            created_date=datetime(2021, 5, 10),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="IT service management and help desk ticketing.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-012a", "Directory.Read.All", APP, H, ferpa=True,
                      desc="Read directory data"),
                _perm("p-012b", "User.Read.All", APP, H, ferpa=True,
                      desc="Read all users' full profiles"),
            ],
            credentials=[
                _secret("cred-012a", "ServiceNow Secret", 55),   # EXPIRING
            ],
            assignment_required=True,
            app_role_assignments=[
                _assignment("ara-012a", "IT Department",    "Group"),
                _assignment("ara-012b", "Help Desk Staff",  "Group"),
                _assignment("ara-012c", "James Smith",      "User"),
            ],
        ),

        # ── 13. Staff Email Notifications ────────────────────────────────────
        EntraApp(
            id="app-013",
            app_id="77777777-0013-0013-0013-777777777777",
            display_name="Staff Email Notifications",
            created_date=datetime(2022, 9, 1),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Automated email notifications for staff announcements.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-013a", "Mail.Read", DEL, M, ferpa=True,
                      desc="Read user mail"),
                _perm("p-013b", "User.Read", DEL, L,
                      desc="Sign in and read user profile"),
            ],
            credentials=[
                _secret("cred-013a", "Notifications Secret", 250),
            ],
        ),

        # ── 14. Google Admin SDK Bridge – Chromebook MDM ──────────────────────
        EntraApp(
            id="app-014",
            app_id="88888888-0014-0014-0014-888888888888",
            display_name="Google Admin SDK Bridge – Chromebook MDM",
            created_date=datetime(2020, 11, 30),
            sign_in_audience="AzureADMyOrg",
            publisher_domain="riverside-usd.edu",
            description="Syncs Chromebook device inventory with Entra for MDM policy.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-014a", "Directory.Read.All", APP, H, ferpa=True,
                      desc="Read directory data"),
                _perm("p-014b", "DeviceManagementApps.ReadWrite.All", APP, H,
                      desc="Read and write Microsoft Intune apps"),
            ],
            credentials=[
                _secret("cred-014a", "MDM Bridge Secret", 87),   # EXPIRING_LATER
                _fed("cred-014b", "MDM Federated Identity", 365),
            ],
        ),

        # ── 15. B2C Student App ───────────────────────────────────────────────
        EntraApp(
            id="app-015",
            app_id="99999999-0015-0015-0015-999999999999",
            display_name="B2C Student App",
            created_date=datetime(2023, 6, 1),
            sign_in_audience="AzureADAndPersonalMicrosoftAccount",
            publisher_domain="riverside-usd.edu",
            description="Student-facing app allowing personal Microsoft account login.",
            owners=[IT_ADMIN],
            permissions=[
                _perm("p-015a", "User.Read", DEL, L,
                      desc="Sign in and read user profile"),
                _perm("p-015b", "offline_access", DEL, L, offline=True,
                      desc="Maintain access to data you have given it access to"),
                _perm("p-015c", "openid", DEL, L, desc="Sign users in"),
            ],
            credentials=[
                _fed("cred-015a", "Student App Federated Identity", 20),  # EXPIRING_SOON
            ],
        ),
    ]


# ── public API ────────────────────────────────────────────────────────────────

def get_tenant_info() -> TenantInfo:
    return TenantInfo(
        tenant_id="mock-tenant-id-riverside-usd",
        tenant_name="Riverside Unified School District",
        display_name="Riverside USD",
    )


def get_apps() -> list[EntraApp]:
    return _build_apps()


def get_app_by_id(app_id: str) -> EntraApp | None:
    return next((a for a in _build_apps() if a.id == app_id), None)
