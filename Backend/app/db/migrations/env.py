"""Alembic environment — connects migrations to our Settings and metadata.

Task S1-F08. This is the standard Alembic ``env.py`` with three deliberate
changes from the generated template:

1. the database URL comes from ``app.core.config.settings``, not ``alembic.ini``,
   so credentials stay out of git and one env var switches environments;
2. ``target_metadata`` points at ``app.db.base_models.Base.metadata``, the module
   that imports every model — autogenerate is blind to models it has not imported;
3. ``render_as_batch=True`` so migrations also run on SQLite.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings

# Base is imported from base_models (not base) because that module's import
# statements are what populate the metadata with tables.
from app.db.base_models import Base

# The alembic.ini object, injected by the alembic runner.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the URL at runtime. set_main_option escapes '%' for us, which matters
# because a generated DB password can legitimately contain one and ConfigParser
# would otherwise read it as interpolation syntax.
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata

# Options shared by the offline and online paths, so the two cannot drift.
#
# compare_type: detect a column type change (String(50) -> String(120)). Off by
#   default, which means such a change silently produces an empty migration.
# compare_server_default: likewise for server-side defaults.
# render_as_batch: SQLite cannot ALTER most column properties, so Alembic must
#   rebuild the table instead. Needed because tests run on SQLite.
_COMMON_OPTIONS = {
    "target_metadata": target_metadata,
    "compare_type": True,
    "compare_server_default": True,
    "render_as_batch": True,
}


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of executing it (``alembic upgrade head --sql``).

    Useful for handing a DBA the exact statements, or for reviewing what a
    migration will do without a database connection.
    """
    context.configure(
        url=settings.database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_COMMON_OPTIONS,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Execute migrations against a live database connection.

    NullPool: this process runs one migration and exits, so a connection pool
    would only hold idle connections open for no benefit.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, **_COMMON_OPTIONS)
        # One transaction for the whole run: if migration 3 of 4 fails, the first
        # two roll back too. PostgreSQL supports transactional DDL, so the
        # database is never left half-migrated.
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
