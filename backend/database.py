
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_database_engine() -> Engine:
    """Create a SQLAlchemy engine for the configured PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    # Support Render URLs that use the legacy postgres:// prefix.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_recycle=1800,
    )


def test_database_connection() -> bool:
    """Verify that PostgreSQL is reachable."""
    engine = get_database_engine()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    finally:
        engine.dispose()
