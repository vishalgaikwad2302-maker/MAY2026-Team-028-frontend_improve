"""Database engine and session factory.

Configures SQLAlchemy engine and sessionmaker supporting SQLite and PostgreSQL,
and provides the get_db generator dependency.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

__all__ = ["SessionLocal", "engine", "get_db"]

connect_args: dict[str, Any] = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.db_echo,
)

if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
