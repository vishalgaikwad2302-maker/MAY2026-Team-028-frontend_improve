"""Unit tests for database session, engine, and SQLite support."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, get_db
from app.models.user import User, UserRole


def test_sqlite_engine_configuration():
    """Verify SQLite engine setup and table creation."""
    # Create all tables on the engine (in-memory SQLite db for testing)
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "users" in tables


def test_get_db_session_lifecycle():
    """Verify get_db session generator opens and closes a session."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    # Perform a simple query
    Base.metadata.create_all(bind=engine)
    count = session.query(User).count()
    assert isinstance(count, int)

    # Close generator
    with pytest.raises(StopIteration):
        next(db_gen)


def test_user_model_instantiation():
    """Verify User ORM model fields and defaults."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_secret",
        full_name="Test User",
        role=UserRole.CITIZEN.value,
    )
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.role == "citizen"
