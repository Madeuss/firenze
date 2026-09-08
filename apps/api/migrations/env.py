"""Alembic wiring.

The URL is never written in alembic.ini: it carries a password, and a file that
carries a password is a file somebody commits eventually. It comes from
settings, which read the environment — unless a caller set one explicitly,
which is how the tests build their schema against a throwaway database.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from firenze.config import settings
from firenze.storage import metadata

config = context.config
if not config.get_main_option("sqlalchemy.url", ""):
    config.set_main_option("sqlalchemy.url", settings.database_url)

# A programmatic caller (the test suite) already owns logging; reconfiguring it
# from alembic.ini underneath pytest would swallow its output.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
