"""PostgreSQL gateway.

No Django model or ORM API is used anywhere in the project. Queries are always
parameterized. Transactions can select serializable/repeatable-read isolation
when a workflow needs stronger guarantees.
"""
from __future__ import annotations

import atexit
import contextlib
import logging
import threading
from collections.abc import Generator, Iterable, Sequence
from typing import Any

from psycopg import Connection, sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import config

logger = logging.getLogger(__name__)

_pool_lock = threading.Lock()

_pool = ConnectionPool(
    conninfo=config.database_url,
    min_size=config.db_pool_min,
    max_size=config.db_pool_max,
    timeout=config.db_connect_timeout,
    kwargs={
        "row_factory": dict_row,
        "autocommit": False,
        "options": (
            f"-c statement_timeout={config.db_statement_timeout_ms} "
            f"-c lock_timeout={config.db_lock_timeout_ms} "
            "-c idle_in_transaction_session_timeout="
            f"{config.db_idle_transaction_timeout_ms}"
        ),
    },
    open=False,
)


def open_pool() -> None:
    if not _pool.closed:
        return
    with _pool_lock:
        if _pool.closed:
            _pool.open(wait=True)


def close_pool() -> None:
    with _pool_lock:
        if not _pool.closed:
            _pool.close()


atexit.register(close_pool)


@contextlib.contextmanager
def connection() -> Generator[Connection[Any], None, None]:
    open_pool()
    with _pool.connection() as conn:
        yield conn


@contextlib.contextmanager
def transaction(
    *, isolation: str | None = None, read_only: bool = False
) -> Generator[Connection[Any], None, None]:
    """Yield a connection inside a transaction and commit/rollback safely."""
    with connection() as conn:
        try:
            with conn.transaction():
                if isolation:
                    normalized = isolation.strip().upper()
                    allowed = {"READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"}
                    if normalized not in allowed:
                        raise ValueError("Unsupported transaction isolation")
                    with conn.cursor() as cur:
                        cur.execute(sql.SQL("SET TRANSACTION ISOLATION LEVEL {}")
                                    .format(sql.SQL(normalized)))
                        if read_only:
                            cur.execute("SET TRANSACTION READ ONLY")
                elif read_only:
                    with conn.cursor() as cur:
                        cur.execute("SET TRANSACTION READ ONLY")
                yield conn
        except Exception:
            logger.exception("Database transaction failed")
            raise


def fetch_one(query: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    with transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchone()


def fetch_all(query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    with transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(query, params or ())
        return list(cur.fetchall())


def execute(
    query: str,
    params: Sequence[Any] | None = None,
    *,
    returning: bool = False,
) -> dict[str, Any] | None:
    with transaction() as conn, conn.cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchone() if returning else None


def execute_many(query: str, rows: Iterable[Sequence[Any]]) -> None:
    with transaction() as conn, conn.cursor() as cur:
        cur.executemany(query, rows)


def ping() -> bool:
    try:
        row = fetch_one("SELECT 1 AS ok")
        return bool(row and row["ok"] == 1)
    except Exception:
        logger.exception("Database ping failed")
        return False
