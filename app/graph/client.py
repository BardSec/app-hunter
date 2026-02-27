"""
Graph API client.

When MOCK_DATA=true the client returns fixture data from mock_data.py without
making any network calls. When MOCK_DATA=false it calls the Microsoft Graph API
using the caller's delegated access token.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.graph import mock_data
from app.graph.schemas import (
    AppCredential,
    AppOwner,
    AppPermission,
    CredentialStatus,
    EntraApp,
    PermissionType,
    RiskLevel,
    TenantInfo,
)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# ── Microsoft Graph permission ID → display name ──────────────────────────────
# Application permissions (type = "Role")
_APP_ROLES: dict[str, str] = {
    "741f803b-c850-494e-b5df-cde7c675a1ca": "User.ReadWrite.All",
    "df021288-bdef-4463-88db-98f22de89214": "User.Read.All",
    "19dbc75e-c2e2-444c-a770-ec69d8559fc7": "Directory.ReadWrite.All",
    "7ab1d382-f21e-4acd-a863-ba3e13f7da61": "Directory.Read.All",
    "e2a3a72e-5f79-4c64-b1b1-878b674786c9": "Mail.ReadWrite",
    "810c84a8-4a9e-49e6-bf7d-12d183f40d01": "Mail.Read",
    "75359482-378d-4052-8f01-80520e7db3cd": "Files.ReadWrite.All",
    "01d4889c-1287-42c6-ac1f-5d1e02578ef6": "Files.Read.All",
    "9492366f-7969-46a4-8d15-ed1a20078fff": "Sites.ReadWrite.All",
    "332a536c-c7ef-4017-ab91-336970924f0d": "Sites.Read.All",
    "a82116e5-55eb-4c41-a434-62fe8a61c773": "Sites.FullControl.All",
    "9e3f62cf-ca93-4989-b6ce-bf83c28f9fe8": "RoleManagement.ReadWrite.Directory",
    "1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9": "Application.ReadWrite.All",
    "dbaae8cf-10b5-4b86-a4a1-f871c94c6695": "GroupMember.ReadWrite.All",
    "98830695-27a2-44f7-8c18-0c3ebc9698f6": "GroupMember.Read.All",
    "62a82d76-70ea-41e2-9197-370581804d09": "Group.ReadWrite.All",
    "5b567255-7703-4780-807c-7be8301ae99b": "Group.Read.All",
    "78145de6-330d-4800-a6ce-494ff2d33d07": "DeviceManagementApps.ReadWrite.All",
    "798ee544-9d2d-430c-a058-570e29e34338": "Calendars.Read",
    "ef54d2bf-783f-4e0f-bca1-3210c4d670f9": "Calendars.ReadWrite",
}

# Delegated permissions (type = "Scope")
_SCOPES: dict[str, str] = {
    "e1fe6dd8-ba31-4d61-89e7-88639da4683d": "User.Read",
    "b4e74841-8e56-480b-be8b-910348b18b4c": "User.ReadWrite",
    "a154be20-db9c-4678-8ab7-66f6cc099a59": "User.Read.All",
    "204e0828-b5ca-4ad8-b9f3-f32a958e7cc4": "User.ReadWrite.All",
    "06da0dbc-49e2-44d2-8312-53f166ab848a": "Directory.Read.All",
    "c5366453-9fb0-48a5-a156-24f0c49a4b84": "Directory.ReadWrite.All",
    "570282fd-fa5c-430d-a7fd-fc8dc98a9dca": "Mail.Read",
    "024d486e-b451-40bb-833d-3e66d98c5c73": "Mail.ReadWrite",
    "df85f4d6-205c-4ac5-a5ea-6bf408dba283": "Files.Read.All",
    "863451e7-0667-486c-a5d6-d135439485f0": "Files.ReadWrite.All",
    "205e70e5-aba6-4c52-a976-6d2d46c48043": "Sites.Read.All",
    "89fe6a52-be36-487e-b7d8-d061c450a026": "Sites.ReadWrite.All",
    "5a54b8b3-347c-476d-8f8e-42d5c7424d29": "Sites.FullControl.All",
    "7427e0e9-2fba-42fe-b0c0-848c9e6a8182": "offline_access",
    "37f7f235-527c-4136-accd-4a02d197296e": "openid",
    "14dad69e-099b-42c9-810b-d002981feec1": "profile",
    "64a6cdd6-aab1-4aad-94b8-3cc8405e90d0": "email",
    "4e46008b-f24c-477d-8fff-7bb4ec7aafe0": "Group.ReadWrite.All",
    "f81125ac-d3b7-4573-a3b2-7099cc39df9e": "GroupMember.ReadWrite.All",
}

GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.rstrip("Z"))
    except (ValueError, AttributeError):
        return None


def _cred_status(end_date: Optional[datetime]) -> tuple[CredentialStatus, Optional[int]]:
    if end_date is None:
        return CredentialStatus.OK, None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = (end_date - now).days
    if delta < 0:
        return CredentialStatus.EXPIRED, delta
    if delta <= 30:
        return CredentialStatus.EXPIRING_SOON, delta
    if delta <= 60:
        return CredentialStatus.EXPIRING, delta
    if delta <= 90:
        return CredentialStatus.EXPIRING_LATER, delta
    return CredentialStatus.OK, delta


class GraphClient:
    def __init__(self, access_token: str):
        self._token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

    # ── public methods ────────────────────────────────────────────────────────

    async def get_tenant_info(self) -> TenantInfo:
        if settings.MOCK_DATA:
            return mock_data.get_tenant_info()
        org = await self._get("/organization?$select=id,displayName")
        item = org["value"][0]
        return TenantInfo(
            tenant_id=item["id"],
            tenant_name=item.get("displayName", "Unknown"),
            display_name=item.get("displayName", "Unknown"),
        )

    async def get_app_registrations(self) -> list[EntraApp]:
        if settings.MOCK_DATA:
            return mock_data.get_apps()

        select = (
            "id,appId,displayName,createdDateTime,signInAudience,"
            "description,publisherDomain,passwordCredentials,keyCredentials,"
            "requiredResourceAccess"
        )
        raw_apps = await self._get_paged(f"/applications?$select={select}&$top=100")
        apps: list[EntraApp] = []
        for raw in raw_apps:
            try:
                app = await self._build_app(raw)
                apps.append(app)
            except Exception:
                pass  # skip individual apps that fail to build
        return apps

    async def get_app_by_id(self, object_id: str) -> Optional[EntraApp]:
        if settings.MOCK_DATA:
            return mock_data.get_app_by_id(object_id)
        select = (
            "id,appId,displayName,createdDateTime,signInAudience,"
            "description,publisherDomain,passwordCredentials,keyCredentials,"
            "requiredResourceAccess"
        )
        try:
            raw = await self._get(f"/applications/{object_id}?$select={select}")
        except httpx.HTTPStatusError:
            return None
        return await self._build_app(raw)

    # ── internal builders ─────────────────────────────────────────────────────

    async def _build_app(self, raw: dict) -> EntraApp:
        obj_id = raw["id"]

        owners = await self._get_owners(obj_id)
        fed_creds = await self._get_fed_creds(obj_id)
        permissions = self._parse_permissions(raw.get("requiredResourceAccess", []))
        credentials = (
            self._parse_secrets(raw.get("passwordCredentials", []))
            + self._parse_certs(raw.get("keyCredentials", []))
            + fed_creds
        )

        return EntraApp(
            id=obj_id,
            app_id=raw.get("appId", ""),
            display_name=raw.get("displayName", ""),
            created_date=_parse_dt(raw.get("createdDateTime")),
            sign_in_audience=raw.get("signInAudience", "AzureADMyOrg"),
            publisher_domain=raw.get("publisherDomain"),
            description=raw.get("description"),
            owners=owners,
            permissions=permissions,
            credentials=credentials,
        )

    async def _get_owners(self, app_object_id: str) -> list[AppOwner]:
        try:
            data = await self._get(
                f"/applications/{app_object_id}/owners"
                "?$select=id,displayName,userPrincipalName"
            )
            return [
                AppOwner(
                    id=o.get("id", ""),
                    display_name=o.get("displayName", ""),
                    user_principal_name=o.get("userPrincipalName"),
                )
                for o in data.get("value", [])
            ]
        except Exception:
            return []

    async def _get_fed_creds(self, app_object_id: str) -> list[AppCredential]:
        try:
            data = await self._get(f"/applications/{app_object_id}/federatedIdentityCredentials")
            creds = []
            for fc in data.get("value", []):
                end = _parse_dt(fc.get("expiresDateTime"))
                status, remaining = _cred_status(end)
                creds.append(
                    AppCredential(
                        key_id=fc.get("id", ""),
                        display_name=fc.get("name", "Federation Credential"),
                        credential_type="federation",
                        end_date=end,
                        status=status,
                        days_until_expiry=remaining,
                    )
                )
            return creds
        except Exception:
            return []

    def _parse_permissions(self, required_resource_access: list[dict]) -> list[AppPermission]:
        perms: list[AppPermission] = []
        for resource in required_resource_access:
            resource_app_id = resource.get("resourceAppId", "")
            is_graph = resource_app_id == GRAPH_APP_ID
            for access in resource.get("resourceAccess", []):
                pid = access.get("id", "")
                ptype_raw = access.get("type", "Scope")
                is_role = ptype_raw == "Role"
                ptype = PermissionType.APPLICATION if is_role else PermissionType.DELEGATED

                if is_graph:
                    name = (_APP_ROLES if is_role else _SCOPES).get(pid, pid)
                else:
                    name = pid  # non-Graph: show raw ID

                perms.append(AppPermission(
                    id=pid,
                    name=name,
                    permission_type=ptype,
                    resource_app_id=resource_app_id,
                ))
        return perms

    def _parse_secrets(self, raw_secrets: list[dict]) -> list[AppCredential]:
        creds = []
        for s in raw_secrets:
            end = _parse_dt(s.get("endDateTime"))
            status, remaining = _cred_status(end)
            creds.append(AppCredential(
                key_id=s.get("keyId", ""),
                display_name=s.get("displayName") or "Client Secret",
                credential_type="secret",
                start_date=_parse_dt(s.get("startDateTime")),
                end_date=end,
                status=status,
                days_until_expiry=remaining,
            ))
        return creds

    def _parse_certs(self, raw_keys: list[dict]) -> list[AppCredential]:
        creds = []
        for k in raw_keys:
            end = _parse_dt(k.get("endDateTime"))
            status, remaining = _cred_status(end)
            creds.append(AppCredential(
                key_id=k.get("keyId", ""),
                display_name=k.get("displayName") or k.get("type", "Certificate"),
                credential_type="certificate",
                start_date=_parse_dt(k.get("startDateTime")),
                end_date=end,
                status=status,
                days_until_expiry=remaining,
            ))
        return creds

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def _get(self, path: str) -> dict:
        url = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, timeout=30)
            resp.raise_for_status()
            return resp.json()

    async def _get_paged(self, path: str) -> list[dict]:
        results: list[dict] = []
        url: Optional[str] = path if path.startswith("http") else f"{GRAPH_BASE}{path}"
        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, headers=self._headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
        return results
