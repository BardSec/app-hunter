"""Tests for the permission risk classification service."""

import pytest

from app.graph.schemas import AppPermission, EntraApp, PermissionType, RiskLevel
from app.services.permission_audit import (
    HIGH_RISK_PERMS,
    MEDIUM_RISK_PERMS,
    FERPA_PERMS,
    classify_permission,
    enrich_permissions,
    app_risk_level,
)


def _make_perm(name: str, ptype: PermissionType = PermissionType.APPLICATION) -> AppPermission:
    return AppPermission(id="test-id", name=name, permission_type=ptype)


def _make_app(perms: list[AppPermission]) -> EntraApp:
    return EntraApp(
        id="app-test",
        app_id="00000000-0000-0000-0000-000000000001",
        display_name="Test App",
        permissions=perms,
    )


class TestClassifyPermission:
    def test_high_risk_permission(self):
        perm = _make_perm("Directory.ReadWrite.All")
        result = classify_permission(perm)
        assert result.risk_level == RiskLevel.HIGH

    def test_medium_risk_permission(self):
        perm = _make_perm("Directory.Read.All")
        result = classify_permission(perm)
        assert result.risk_level == RiskLevel.MEDIUM

    def test_openid_is_none_risk(self):
        perm = _make_perm("openid", PermissionType.DELEGATED)
        result = classify_permission(perm)
        assert result.risk_level == RiskLevel.NONE

    def test_user_read_is_none_risk(self):
        perm = _make_perm("User.Read", PermissionType.DELEGATED)
        result = classify_permission(perm)
        assert result.risk_level == RiskLevel.NONE

    def test_offline_access_flagged(self):
        perm = _make_perm("offline_access", PermissionType.DELEGATED)
        result = classify_permission(perm)
        assert result.is_offline_access is True

    def test_ferpa_relevant_flagged(self):
        for perm_name in FERPA_PERMS:
            perm = _make_perm(perm_name)
            result = classify_permission(perm)
            assert result.is_ferpa_relevant is True, f"{perm_name} should be FERPA-relevant"

    def test_non_ferpa_permission_not_flagged(self):
        perm = _make_perm("DeviceManagementApps.ReadWrite.All")
        result = classify_permission(perm)
        assert result.is_ferpa_relevant is False

    def test_all_high_risk_classified_correctly(self):
        for perm_name in HIGH_RISK_PERMS:
            perm = _make_perm(perm_name)
            result = classify_permission(perm)
            assert result.risk_level == RiskLevel.HIGH, f"{perm_name} should be HIGH risk"

    def test_all_medium_risk_classified_correctly(self):
        for perm_name in MEDIUM_RISK_PERMS:
            perm = _make_perm(perm_name)
            result = classify_permission(perm)
            assert result.risk_level == RiskLevel.MEDIUM, f"{perm_name} should be MEDIUM risk"


class TestEnrichPermissions:
    def test_app_with_high_risk_perm_gets_high_level(self):
        app = _make_app([
            _make_perm("User.ReadWrite.All"),
            _make_perm("User.Read", PermissionType.DELEGATED),
        ])
        result = enrich_permissions(app)
        assert result.risk_level == RiskLevel.HIGH
        assert result.has_high_risk_permissions is True

    def test_app_with_only_medium_gets_medium_level(self):
        app = _make_app([_make_perm("User.Read.All")])
        result = enrich_permissions(app)
        assert result.risk_level == RiskLevel.MEDIUM
        assert result.has_high_risk_permissions is False

    def test_app_with_no_perms_gets_none_level(self):
        app = _make_app([])
        result = enrich_permissions(app)
        assert result.risk_level == RiskLevel.NONE

    def test_offline_access_detected(self):
        app = _make_app([_make_perm("offline_access", PermissionType.DELEGATED)])
        result = enrich_permissions(app)
        assert result.has_offline_access is True

    def test_permissions_are_classified(self):
        app = _make_app([_make_perm("Mail.ReadWrite")])
        result = enrich_permissions(app)
        assert result.permissions[0].risk_level == RiskLevel.HIGH
