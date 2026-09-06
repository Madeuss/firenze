"""One engine, built from configuration.

`pool_pre_ping` because the managed database sits behind a network that drops
idle connections, and a stale one surfaces as a failed turn rather than as a
reconnect (ADR-0002).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import Connection

from firenze.config import settings


@cache
def engine(url: str | None = None) -> Engine:
    return create_engine(url or settings.database_url, pool_pre_ping=True, future=True)


@contextmanager
def transaction(url: str | None = None) -> Iterator[Connection]:
    """A unit of work. One turn is one of these."""
    with engine(url).begin() as connection:
        yield connection
