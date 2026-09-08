"""One throwaway database per test run, built by the migrations.

The suite used to call `metadata.create_all` against the development database.
That reads as harmless — the fixtures roll their transactions back — but DDL is
not transactional the same way, and `create_all` commits. It bit twice:

- renaming `statements` to `turns` made pytest create the new table beside the
  old one, and the next `alembic upgrade` failed on a table it had never made;
- adding a column to `matches` failed the other way, because `create_all`
  creates a missing *table* and never alters one that exists.

Both are the same fault: the schema had two owners that did not talk. So the
tests now build the schema the way production does — `alembic upgrade head` —
against a database created for the run and dropped at the end of it. The
migration chain gets exercised on every `make check` instead of on the day it
is deployed.
"""

import os
import pathlib
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

SERVER_URL = os.environ.get(
    "FIRENZE_TEST_DATABASE_URL",
    "postgresql+psycopg://firenze:firenze@localhost:5433/firenze",
)
TEST_DATABASE = os.environ.get("FIRENZE_TEST_DATABASE_NAME", "firenze_test")


def _named(url: str, database: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{database}"


TEST_URL = _named(SERVER_URL, TEST_DATABASE)


def reachable() -> bool:
    """A short timeout on purpose: without one, a missing database costs four
    minutes of retries before the suite decides to skip."""
    try:
        create_engine(SERVER_URL, connect_args={"connect_timeout": 2}).connect().close()
    except OperationalError:
        return False
    return True


needs_database = pytest.mark.skipif(
    not reachable(), reason=f"no database at {SERVER_URL} — start one with `make dev`"
)


def _migrate(url: str) -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    # pytest owns logging here; alembic.ini would take it over.
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Drop, create, migrate. Dropped again so a failed run leaves nothing behind.

    Recreated rather than reused: a database that survives between runs carries
    whatever schema the last branch left in it, which is the thing this fixture
    exists to stop happening.
    """
    if not reachable():
        pytest.skip(f"no database at {SERVER_URL}")

    admin = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        # FORCE because a connection left open by a crashed run would otherwise
        # keep the old database alive and fail the drop.
        connection.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{TEST_DATABASE}"'))

    _migrate(TEST_URL)
    try:
        yield TEST_URL
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)'))
        admin.dispose()
