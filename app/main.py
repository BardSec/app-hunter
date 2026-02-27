import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import apps, auth, compliance, credentials, dashboard, permissions

# Import templates_config early so filters are registered before any request
import app.templates_config  # noqa: F401


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.makedirs("data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(apps.router, prefix="/apps", tags=["apps"])
app.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
app.include_router(credentials.router, prefix="/credentials", tags=["credentials"])
app.include_router(compliance.router, prefix="/compliance", tags=["compliance"])


# ── Global 401 → redirect to login ────────────────────────────────────────────
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return RedirectResponse(url="/auth/login", status_code=302)
