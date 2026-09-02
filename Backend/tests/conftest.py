"""Shared pytest fixtures."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import settings
from app.db.base import Base
from app.main import create_app

__all__ = ["client", "db_session"]


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path: Path) -> Generator[None, None, None]:
    """Point evidence-photo uploads at a per-test tmp dir instead of ./uploads.

    Without this every upload test would write real files into the repo
    working directory and never clean them up.
    """
    original = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"
    try:
        yield
    finally:
        settings.upload_dir = original


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create an isolated in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency pointing to test session."""
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
