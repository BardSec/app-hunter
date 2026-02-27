"""
FastAPI dependency that returns the current user dict from the session.

In mock mode a synthetic admin user is returned so authentication is
completely bypassed — no Microsoft credentials needed.
"""

from fastapi import HTTPException, Request

from app.config import settings

_MOCK_USER = {
    "id": "mock-user-001",
    "name": "Demo Admin",
    "username": "demo@riverside-usd.edu",
    "tenant_id": "mock-tenant-id-riverside-usd",
    "tenant_name": "Riverside Unified School District",
    "access_token": "mock-access-token",
}


def get_current_user(request: Request) -> dict:
    """
    Returns the session user or raises 401 (caught by the global handler
    and redirected to /auth/login).
    """
    if settings.MOCK_DATA:
        return _MOCK_USER

    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
