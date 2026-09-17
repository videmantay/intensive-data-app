from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, Request
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "FieldOps API"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Which database adapter to use. SQL is written in SAP HANA dialect either way.
    db_backend: Literal["sqlite", "hana"] = "sqlite"

    sqlite_path: Path = BACKEND_DIR / "data" / "app.db"

    # Assistant (OpenAI). Set OPENAI_API_KEY in backend/.env; the model name is
    # whatever your OpenAI account has access to.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""  # optional: Azure OpenAI or another compatible gateway
    openai_timeout_seconds: float = 60.0

    hana_host: str = "localhost"
    hana_port: int = 30015
    hana_user: str = ""
    hana_password: str = ""
    hana_schema: str | None = None
    hana_encrypt: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_app_settings(request: Request) -> Settings:
    """The settings this app was created with (tests can pass their own)."""
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]
