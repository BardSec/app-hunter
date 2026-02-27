"""Tests for the credential expiry classification service."""

from datetime import datetime, timedelta, timezone

import pytest

from app.graph.schemas import AppCredential, CredentialStatus, EntraApp
from app.services.credential_scan import (
    enrich_credentials,
    worst_credential_status,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _cred(status: CredentialStatus, days: int) -> AppCredential:
    end = _now() + timedelta(days=days)
    return AppCredential(
        key_id="k1",
        display_name="Test Cred",
        credential_type="secret",
        end_date=end,
        status=status,
        days_until_expiry=days,
    )


def _app(creds: list[AppCredential]) -> EntraApp:
    return EntraApp(
        id="app-test",
        app_id="00000000-0000-0000-0000-000000000001",
        display_name="Test App",
        credentials=creds,
    )


class TestWorstCredentialStatus:
    def test_no_credentials_returns_ok(self):
        assert worst_credential_status([]) == CredentialStatus.OK

    def test_single_expired(self):
        creds = [_cred(CredentialStatus.EXPIRED, -5)]
        assert worst_credential_status(creds) == CredentialStatus.EXPIRED

    def test_expired_beats_expiring_soon(self):
        creds = [
            _cred(CredentialStatus.EXPIRING_SOON, 10),
            _cred(CredentialStatus.EXPIRED, -2),
        ]
        assert worst_credential_status(creds) == CredentialStatus.EXPIRED

    def test_expiring_soon_beats_ok(self):
        creds = [
            _cred(CredentialStatus.OK, 200),
            _cred(CredentialStatus.EXPIRING_SOON, 5),
        ]
        assert worst_credential_status(creds) == CredentialStatus.EXPIRING_SOON

    def test_all_ok(self):
        creds = [_cred(CredentialStatus.OK, 365)]
        assert worst_credential_status(creds) == CredentialStatus.OK


class TestEnrichCredentials:
    def test_expired_credential_sets_flag(self):
        app = _app([_cred(CredentialStatus.EXPIRED, -10)])
        result = enrich_credentials(app)
        assert result.has_expired_credentials is True
        assert result.has_expiring_credentials is False

    def test_expiring_soon_credential_sets_flag(self):
        app = _app([_cred(CredentialStatus.EXPIRING_SOON, 15)])
        result = enrich_credentials(app)
        assert result.has_expired_credentials is False
        assert result.has_expiring_credentials is True

    def test_expiring_later_sets_expiring_flag(self):
        app = _app([_cred(CredentialStatus.EXPIRING_LATER, 80)])
        result = enrich_credentials(app)
        assert result.has_expiring_credentials is True

    def test_ok_credentials_no_flags(self):
        app = _app([_cred(CredentialStatus.OK, 200)])
        result = enrich_credentials(app)
        assert result.has_expired_credentials is False
        assert result.has_expiring_credentials is False

    def test_no_credentials_no_flags(self):
        app = _app([])
        result = enrich_credentials(app)
        assert result.has_expired_credentials is False
        assert result.has_expiring_credentials is False

    def test_mixed_expired_and_ok(self):
        app = _app([
            _cred(CredentialStatus.OK, 300),
            _cred(CredentialStatus.EXPIRED, -5),
        ])
        result = enrich_credentials(app)
        assert result.has_expired_credentials is True
