"""Unit tests for app/core/config.py (S1-F02).

Configuration is the kind of code that looks too simple to test right up until a
comma-separated env var silently parses as a single string and CORS breaks in
staging only. These tests pin the parsing rules and the production guard.

Note the pattern: ``Settings(_env_file=None, ...)`` constructs an isolated
instance. Passing ``_env_file=None`` stops pydantic-settings reading the
developer's real ``.env``, which would make results machine-dependent.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**overrides) -> Settings:
    """Build a Settings instance from explicit values only."""
    return Settings(_env_file=None, **overrides)


class TestCorsParsing:
    """The comma-separated-string decision, verified."""

    def test_single_origin(self) -> None:
        assert make_settings(cors_origins="http://localhost:5173").cors_origin_list == [
            "http://localhost:5173"
        ]

    def test_multiple_origins_are_split(self) -> None:
        settings = make_settings(cors_origins="http://localhost:5173,https://smartsweep.example")
        assert settings.cors_origin_list == [
            "http://localhost:5173",
            "https://smartsweep.example",
        ]

    def test_surrounding_whitespace_is_stripped(self) -> None:
        """`.env` files routinely gain stray spaces after a comma."""
        settings = make_settings(cors_origins=" http://a.test , http://b.test ")
        assert settings.cors_origin_list == ["http://a.test", "http://b.test"]

    def test_empty_string_yields_no_origins(self) -> None:
        """Not `[""]` — an empty origin would be sent as a literal header value."""
        assert make_settings(cors_origins="").cors_origin_list == []

    def test_trailing_comma_does_not_produce_a_blank_origin(self) -> None:
        assert make_settings(cors_origins="http://a.test,").cors_origin_list == ["http://a.test"]


class TestUploadRules:
    def test_mime_types_parse_to_a_lowercased_set(self) -> None:
        settings = make_settings(upload_allowed_mime_types="image/JPEG, image/png")
        assert settings.upload_allowed_mime_type_set == {"image/jpeg", "image/png"}

    def test_default_size_cap_is_five_megabytes(self) -> None:
        """Plan safe-default 6. A change here must be mirrored in the OpenAPI 413."""
        assert make_settings().upload_max_bytes == 5 * 1024 * 1024


class TestDuplicateDetectionThresholds:
    def test_defaults_match_the_frontend_util(self) -> None:
        """Parity with Frontend/src/utils/duplicateDetection.js — 200 m / 0.6 / 0.35.

        If this test fails, the server and the browser disagree about what counts
        as a duplicate, and the citizen sees one answer pre-submit and another
        after. Change both sides or neither.
        """
        settings = make_settings()
        assert settings.duplicate_radius_meters == 200.0
        assert settings.duplicate_text_similarity_threshold == 0.6
        assert settings.duplicate_score_threshold == 0.35


class TestEnvironmentBehaviour:
    def test_docs_enabled_in_dev_and_test(self) -> None:
        assert make_settings(env="dev").docs_enabled is True
        assert make_settings(env="test").docs_enabled is True

    def test_docs_disabled_in_prod(self) -> None:
        """/docs is an interactive client for every admin endpoint."""
        assert make_settings(env="prod", jwt_secret_key="a-real-secret").docs_enabled is False

    def test_sqlite_url_is_detected(self) -> None:
        assert make_settings(database_url="sqlite:///:memory:").is_sqlite is True

    def test_postgres_url_is_not_sqlite(self) -> None:
        url = "postgresql+psycopg://u:p@localhost:5432/db"
        assert make_settings(database_url=url).is_sqlite is False

    def test_unknown_env_is_rejected(self) -> None:
        """Literal typing catches `ENV=production` (we spell it `prod`)."""
        with pytest.raises(ValidationError):
            make_settings(env="production")


class TestProductionSecretGuard:
    """Refusing to boot beats booting insecurely."""

    @pytest.mark.parametrize("weak", ["change-me", "CHANGE-ME", "changeme", "secret", ""])
    def test_placeholder_secret_rejected_in_prod(self, weak: str) -> None:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
            make_settings(env="prod", jwt_secret_key=weak)

    def test_real_secret_accepted_in_prod(self) -> None:
        settings = make_settings(env="prod", jwt_secret_key="Zx8-not-a-placeholder-value")
        assert settings.env == "prod"

    def test_placeholder_allowed_in_dev(self) -> None:
        """Local development must not need a secret-generation step."""
        assert make_settings(env="dev", jwt_secret_key="change-me").jwt_secret_key == "change-me"


class TestPaginationBounds:
    def test_default_page_size_cannot_exceed_max(self) -> None:
        with pytest.raises(ValidationError, match="DEFAULT_PAGE_SIZE"):
            make_settings(default_page_size=50, max_page_size=20)

    def test_zero_page_size_is_rejected(self) -> None:
        """page_size=0 would make total_pages a division by zero downstream."""
        with pytest.raises(ValidationError):
            make_settings(default_page_size=0)
