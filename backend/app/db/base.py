"""SQLAlchemy database setup (SQLite dev default, PostgreSQL-compatible)."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and ensure runtime directories exist."""
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite"):
        # Ensure the SQLite parent directory exists (any path shape).
        from pathlib import Path

        db_file = settings.database_url.split("///", 1)[-1]
        if db_file and db_file != ":memory:":
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    from app.db import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
