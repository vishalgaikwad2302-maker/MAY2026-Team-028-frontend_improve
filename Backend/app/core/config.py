"""Environment-driven application settings (Pydantic Settings).

The only place environment variables are read. Nothing else in the codebase
should touch ``os.environ`` — import ``settings`` from here instead. That keeps
configuration testable (override the object) and discoverable (one file lists
every knob the service has).

Precedence, highest first: real environment variables, then ``.env``, then the
defaults below. Defaults are safe for local development only.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings", "settings"]

# Weak secrets that must never reach a deployed environment. Kept as a set so
# the production guard below is a single membership test.
_PLACEHOLDER_SECRETS = {"change-me", "changeme", "secret", ""}


class Settings(BaseSettings):
    """Validated application configuration.

    Field names are lower_snake_case; environment variables are the same names
    upper-cased (``database_url`` <- ``DATABASE_URL``) because matching is
    case-insensitive.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Ignore unrelated variables in the shell/CI environment rather than
        # exploding on them.
        extra="ignore",
    )

    # --- Application ---
    env: Literal["dev", "test", "prod"] = "dev"
    project_name: str = "SmartSweep API"
    api_v1_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- Database ---
    database_url: str = "sqlite:///./smartsweep.db"
    # Echo every SQL statement. Useful when debugging a query, far too noisy
    # otherwise, so it is opt-in via the environment.
    db_echo: bool = False

    # --- Auth (JWT) ---
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # --- CORS ---
    # Deliberately a comma-separated string, not a ``list[str]``. pydantic-settings
    # tries to JSON-decode complex types read from the environment, so a plain
    # ``CORS_ORIGINS=http://localhost:5173`` would raise a parse error. Read the
    # parsed value through ``cors_origin_list`` below.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://localhost:4173"
    )

    # --- File storage (local disk; no S3/CDN in this project) ---
    upload_dir: Path = Path("./uploads")
    upload_max_bytes: int = 5 * 1024 * 1024  # 5 MB cap per photo (US-03)
    upload_allowed_mime_types: str = "image/jpeg,image/png,image/webp"

    # --- Duplicate detection (US-05, US-06) ---
    # These three MUST stay numerically identical to the frontend's
    # utils/duplicateDetection.js, or the advisory shown pre-submit will not
    # match what the server decides. They live in config precisely so the two
    # sides can be checked against one number rather than a magic literal.
    duplicate_radius_meters: float = 200.0
    duplicate_text_similarity_threshold: float = 0.6
    duplicate_score_threshold: float = 0.35

    # --- Pagination ---
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=500)

    # --- External integrations (Sprint 2) ---
    # Optional so Sprint 1 runs without them. Code that uses these must degrade
    # gracefully when they are unset — see plan section 5b.
    anthropic_api_key: str | None = None
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "SmartSweep/0.1 (team-028 academic project)"

    # ---------------------------------------------------------------- helpers

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list, blanks stripped."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_allowed_mime_type_set(self) -> set[str]:
        """Permitted upload content types as a set."""
        return {m.strip().lower() for m in self.upload_allowed_mime_types.split(",") if m.strip()}

    @property
    def is_sqlite(self) -> bool:
        """True when pointed at SQLite (the fast path for unit/API tests)."""
        return self.database_url.startswith("sqlite")

    @property
    def docs_enabled(self) -> bool:
        """Serve Swagger UI everywhere except production."""
        return self.env != "prod"

    # ------------------------------------------------------------ validation

    @model_validator(mode="after")
    def _forbid_placeholder_secret_in_prod(self) -> "Settings":
        """Fail fast rather than deploy with a guessable signing key.

        A weak JWT secret means anyone can mint an admin token. Catching it at
        startup turns a silent security hole into an obvious crash.
        """
        if self.env == "prod" and self.jwt_secret_key.strip().lower() in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY is still a placeholder while ENV=prod. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        return self

    @model_validator(mode="after")
    def _normalize_database_url(self) -> "Settings":
        """Normalize Postgres URLs (e.g. from Render/Heroku) to SQLAlchemy 2.0 psycopg3 dialect."""
        url = self.database_url.strip().strip("'\"")
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        self.database_url = url
        return self

    @model_validator(mode="after")
    def _page_size_bounds_are_coherent(self) -> "Settings":
        if self.default_page_size > self.max_page_size:
            raise ValueError("DEFAULT_PAGE_SIZE cannot exceed MAX_PAGE_SIZE")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings singleton.

    Cached so the ``.env`` file is parsed once. Tests that need different
    configuration should call ``get_settings.cache_clear()`` after patching the
    environment, or override this as a FastAPI dependency.
    """
    return Settings()


# Import-time convenience for modules that only ever need the live settings.
# Prefer ``get_settings`` as a FastAPI dependency where overriding matters.
settings = get_settings()
