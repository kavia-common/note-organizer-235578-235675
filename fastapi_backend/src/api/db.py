from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.api.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base."""


def _get_engine():
    settings = get_settings()
    if not settings.postgres_url:
        raise RuntimeError(
            "Database not configured. Set POSTGRES_URL or POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/POSTGRES_PORT."
        )
    # Note: use sync engine for simplicity; psycopg2 driver.
    return create_engine(settings.postgres_url, pool_pre_ping=True)


engine = _get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# PUBLIC_INTERFACE
def get_db() -> Generator:
    """FastAPI dependency to provide a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
