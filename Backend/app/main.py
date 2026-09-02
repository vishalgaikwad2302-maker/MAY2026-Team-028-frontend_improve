"""FastAPI application entry point.

Responsibility: build the FastAPI app (app factory), attach middleware,
include the versioned API router, and register exception handlers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.middleware import RequestContextMiddleware

__all__ = ["app", "create_app"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and seed demo data on application startup."""
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    """FastAPI application factory."""
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.project_name,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # Middleware runs in reverse registration order (last added = outermost),
    # so request-id/access-log wraps CORS to time and tag the whole response
    # including CORS headers.
    cors_origins = settings.cors_origin_list
    cors_regex = r"^https?://.*"
    if "*" in cors_origins:
        cors_origins = []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=cors_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    # Register domain & framework exception handlers
    register_exception_handlers(app)

    # Include versioned API routers
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # Serve uploaded evidence photos. save_upload() (S2-F05) guarantees every
    # filename under this directory is a random uuid4 + known-good extension,
    # so nothing user-controlled ever reaches this mount.
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    return app


app = create_app()
