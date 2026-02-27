"""Tests for the FERPA / COPPA compliance scoring service."""

import pytest

from app.graph.schemas import AppOwner, AppPermission, EntraApp, PermissionType, RiskLevel
from app.services.compliance import (
    compute_ferpa_risk,
    enrich_compliance,
    ferpa_risk_level,
    is_ferpa_relevant,
)


def _perm(name: str, ptype: PermissionType, risk: RiskLevel, ferpa: bool = False, offline: bool = False) -> AppPermission:
    return AppPermission(
        id="p-test",
        name=name,
        permission_type=ptype,
        risk_level=risk,
        is_ferpa_relevant=ferpa,
        is_offline_access=offline,
    )


def _app(**kwargs) -> EntraApp:
    defaults = dict(
        id="app-test",
        app_id="00000000-0000-0000-0000-000000000001",
        display_name="Test App",
        sign_in_audience="AzureADMyOrg",
        owners=[AppOwner(id="o1", display_name="Admin")],
        permissions=[],
    )
    defaults.update(kwargs)
    return EntraApp(**defaults)


class TestIsferpaRelevant:
    def test_app_with_ferpa_perm_is_relevant(self):
        app = _app(permissions=[
            _perm("Directory.Read.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True)
        ])
        assert is_ferpa_relevant(app) is True

    def test_app_with_offline_access_is_relevant(self):
        app = _app(
            permissions=[_perm("offline_access", PermissionType.DELEGATED, RiskLevel.LOW, offline=True)],
            has_offline_access=True,
        )
        assert is_ferpa_relevant(app) is True

    def test_app_with_only_basic_perms_is_not_relevant(self):
        app = _app(permissions=[
            _perm("User.Read", PermissionType.DELEGATED, RiskLevel.NONE, ferpa=False)
        ])
        assert is_ferpa_relevant(app) is False


class TestComputeFerpaRisk:
    def test_high_risk_ferpa_perm_adds_3_points(self):
        app = _app(permissions=[
            _perm("Directory.ReadWrite.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True)
        ])
        score, factors = compute_ferpa_risk(app)
        assert score == 3
        assert any("Directory.ReadWrite.All" in f for f in factors)

    def test_medium_risk_ferpa_perm_adds_2_points(self):
        app = _app(permissions=[
            _perm("Mail.Read", PermissionType.APPLICATION, RiskLevel.MEDIUM, ferpa=True)
        ])
        score, _ = compute_ferpa_risk(app)
        assert score == 2

    def test_ownerless_adds_2_points(self):
        app = _app(owners=[], is_ownerless=True, permissions=[
            _perm("User.Read.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True)
        ])
        score, factors = compute_ferpa_risk(app)
        assert score >= 5   # 3 (HIGH ferpa) + 2 (ownerless)
        assert any("owner" in f.lower() for f in factors)

    def test_external_audience_adds_2_points(self):
        app = _app(
            sign_in_audience="AzureADMultipleOrgs",
            is_external_facing=True,
            permissions=[
                _perm("User.Read.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True)
            ],
        )
        score, factors = compute_ferpa_risk(app)
        assert score >= 5
        assert any("audience" in f.lower() for f in factors)

    def test_no_ferpa_perms_score_zero(self):
        app = _app(permissions=[
            _perm("User.Read", PermissionType.DELEGATED, RiskLevel.NONE)
        ])
        score, factors = compute_ferpa_risk(app)
        assert score == 0
        assert factors == []

    def test_multiple_ferpa_perms_accumulate(self):
        app = _app(permissions=[
            _perm("Directory.ReadWrite.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True),
            _perm("User.ReadWrite.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True),
            _perm("Mail.Read", PermissionType.APPLICATION, RiskLevel.MEDIUM, ferpa=True),
        ])
        score, _ = compute_ferpa_risk(app)
        assert score == 8   # 3 + 3 + 2


class TestFerpaRiskLevel:
    def test_high_threshold(self):
        assert ferpa_risk_level(8) == RiskLevel.HIGH
        assert ferpa_risk_level(10) == RiskLevel.HIGH

    def test_medium_threshold(self):
        assert ferpa_risk_level(4) == RiskLevel.MEDIUM
        assert ferpa_risk_level(7) == RiskLevel.MEDIUM

    def test_low_threshold(self):
        assert ferpa_risk_level(1) == RiskLevel.LOW
        assert ferpa_risk_level(3) == RiskLevel.LOW

    def test_zero_is_none(self):
        assert ferpa_risk_level(0) == RiskLevel.NONE


class TestEnrichCompliance:
    def test_external_audience_sets_flag(self):
        app = _app(sign_in_audience="AzureADAndPersonalMicrosoftAccount")
        result = enrich_compliance(app)
        assert result.is_external_facing is True

    def test_internal_audience_does_not_set_flag(self):
        app = _app(sign_in_audience="AzureADMyOrg")
        result = enrich_compliance(app)
        assert result.is_external_facing is False

    def test_score_and_factors_populated(self):
        app = _app(permissions=[
            _perm("User.ReadWrite.All", PermissionType.APPLICATION, RiskLevel.HIGH, ferpa=True)
        ])
        result = enrich_compliance(app)
        assert result.ferpa_risk_score > 0
        assert len(result.ferpa_risk_factors) > 0
