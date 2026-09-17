from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.assistant.router import router as assistant_router
from app.config import Settings, get_settings
from app.db import create_database
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
        app.state.database = create_database(settings)
        run_migrations(app.state.database)
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan, generate_unique_id_function=_operation_id)
    app.state.settings = settings  # endpoints read this via the AppSettings dependency
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
            db_ok = request.app.state.database.ping()
        except Exception:
            db_ok = False
        return Health(status="ok", database=f"{settings.db_backend} ({'up' if db_ok else 'down'})")

    api.include_router(items_router)
    api.include_router(assistant_router)
    app.include_router(api)
    return app


app = create_app()
