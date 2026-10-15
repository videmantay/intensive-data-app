import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app.analytics.router import router as analytics_router
from app.assistant.router import router as assistant_router
from app.auth.deps import require_user
from app.auth.router import router as auth_router
from app.config import Settings, get_settings
from app.dashboards.router import router as dashboards_router
from app.db import create_db_engine, ping
from app.db.migrate import run_migrations
from app.items.router import router as items_router


class Health(BaseModel):
    status: str
    database: str


def _operation_id(route: APIRoute) -> str:
    # Use the endpoint function name (e.g. "list_items") so the generated frontend
    # client gets readable names instead of "list_items_api_items_get".
    return route.name


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_db_engine(settings)
        app.state.engine = engine
        run_migrations(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan, generate_unique_id_function=_operation_id)
    app.state.settings = settings  # endpoints read this via the AppSettings dependency
    secret_key = settings.secret_key
    if not secret_key:
        logging.getLogger(__name__).warning("SECRET_KEY is not set; sessions end when the API restarts")
        secret_key = secrets.token_urlsafe(32)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="fieldops_session",
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.session_https_only,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api")

    @api.get("/health", tags=["health"], response_model=Health)
    def health(request: Request):
        try:
            db_ok = ping(request.app.state.engine)
        except Exception:
            db_ok = False
        return Health(status="ok", database=f"{settings.db_backend} ({'up' if db_ok else 'down'})")

    # Everything except health and sign-in needs a signed-in user
    signed_in = [Depends(require_user)]
    api.include_router(auth_router)
    api.include_router(items_router, dependencies=signed_in)
    api.include_router(analytics_router, dependencies=signed_in)
    api.include_router(dashboards_router, dependencies=signed_in)
    api.include_router(assistant_router, dependencies=signed_in)
    app.include_router(api)
    return app


app = create_app()
