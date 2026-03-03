import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application configuration loaded from environment variables.

    Prefer the standard POSTGRES_* env vars from the postgres_database container.
    As a fallback for local dev, we also support reading the URL from
    ../postgres_database/db_connection.txt (contains `psql postgresql://...`).
    """

    app_title: str = Field(default="Notes API", description="OpenAPI title.")
    app_version: str = Field(default="1.0.0", description="OpenAPI version.")
    app_description: str = Field(
        default=(
            "Backend API for a notes application. "
            "Provides JWT auth, notes CRUD with pin/favorite, tags CRUD, and note-tag relations."
        ),
        description="OpenAPI description.",
    )

    # Security
    jwt_secret_key: str = Field(
        default="CHANGE_ME",
        description=(
            "JWT signing secret. MUST be overridden in production via env var JWT_SECRET_KEY."
        ),
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_exp_minutes: int = Field(
        default=60 * 24 * 7, description="Access token expiry in minutes."
    )

    # Database
    postgres_url: Optional[str] = Field(
        default=None,
        description=(
            "SQLAlchemy database URL. If not set, it is constructed from POSTGRES_* vars, "
            "or read from postgres_database/db_connection.txt as fallback."
        ),
    )
    postgres_user: Optional[str] = Field(default=None, description="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default=None, description="POSTGRES_PASSWORD")
    postgres_db: Optional[str] = Field(default=None, description="POSTGRES_DB")
    postgres_port: Optional[str] = Field(default=None, description="POSTGRES_PORT")
    postgres_host: str = Field(
        default="localhost",
        description="Host for Postgres. Typically 'localhost' in this environment.",
    )

    cors_allow_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins. Use '*' for all.",
    )


def _read_db_url_from_db_connection_txt() -> Optional[str]:
    """Try to read a Postgres URL from postgres_database/db_connection.txt.

    db_connection.txt contains: `psql postgresql://user:pass@host:port/db`
    We extract the URL portion.
    """
    candidates = [
        # When running within monorepo workspace
        Path(__file__).resolve().parents[4] / "note-organizer-235578-235673" / "postgres_database" / "db_connection.txt",
        # Relative heuristic in case workspace naming changes
        Path(__file__).resolve().parents[4] / "postgres_database" / "db_connection.txt",
        Path(__file__).resolve().parents[3] / "postgres_database" / "db_connection.txt",
    ]
    for p in candidates:
        try:
            if p.exists():
                line = p.read_text(encoding="utf-8").strip()
                if not line:
                    continue
                # Expect "psql <url>"
                if line.startswith("psql "):
                    return line.split("psql ", 1)[1].strip()
                # Or raw URL
                if line.startswith("postgresql://") or line.startswith("postgres://"):
                    return line
        except Exception:
            continue
    return None


def _build_postgres_url_from_parts(
    user: Optional[str],
    password: Optional[str],
    host: str,
    port: Optional[str],
    db: Optional[str],
) -> Optional[str]:
    """Build a SQLAlchemy Postgres URL from discrete env vars."""
    if not (user and password and port and db):
        return None
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


@lru_cache
def get_settings() -> Settings:
    """PUBLIC_INTERFACE
    Load and cache application settings.

    Returns:
        Settings: validated settings object.
    """
    # read env
    s = Settings(
        app_title=os.getenv("APP_TITLE", "Notes API"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        app_description=os.getenv("APP_DESCRIPTION", Settings().app_description),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "CHANGE_ME"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_exp_minutes=int(os.getenv("ACCESS_TOKEN_EXP_MINUTES", str(60 * 24 * 7))),
        postgres_url=os.getenv("POSTGRES_URL"),
        postgres_user=os.getenv("POSTGRES_USER"),
        postgres_password=os.getenv("POSTGRES_PASSWORD"),
        postgres_db=os.getenv("POSTGRES_DB"),
        postgres_port=os.getenv("POSTGRES_PORT"),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        cors_allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*"),
    )

    if s.postgres_url:
        # Ensure SQLAlchemy driver prefix is present
        if s.postgres_url.startswith("postgresql://") or s.postgres_url.startswith("postgres://"):
            s.postgres_url = s.postgres_url.replace("postgres://", "postgresql://", 1)
            s.postgres_url = s.postgres_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return s

    built = _build_postgres_url_from_parts(
        user=s.postgres_user,
        password=s.postgres_password,
        host=s.postgres_host,
        port=s.postgres_port,
        db=s.postgres_db,
    )
    if built:
        s.postgres_url = built
        return s

    fallback = _read_db_url_from_db_connection_txt()
    if fallback:
        fallback = fallback.replace("postgres://", "postgresql://", 1)
        if fallback.startswith("postgresql://"):
            fallback = fallback.replace("postgresql://", "postgresql+psycopg2://", 1)
        s.postgres_url = fallback
        return s

    # Leave as None; app startup will raise a helpful error.
    return s
