"""Elasticsearch ticket index and query gateway.

The project remains fully usable with PostgreSQL-only search. When
``ELASTICSEARCH_ENABLED=true``, only the public ticket-search operation is
routed through Elasticsearch, as required by Phase 4 of the assignment.
PostgreSQL remains the source of truth. A transactional SQL outbox plus a
periodic full reconciliation keeps the search index synchronized without
coupling database commits to network availability.
"""
from __future__ import annotations

import base64
import contextlib
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from collections.abc import Generator
from typing import Any, Mapping

import database
from config import config

logger = logging.getLogger(__name__)
_INDEX_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,199}$")


class SearchEngineError(RuntimeError):
    """Raised when Elasticsearch cannot safely complete an operation."""


def _index_alias() -> str:
    value = config.elasticsearch_index.lower()
    if not _INDEX_RE.fullmatch(value):
        raise SearchEngineError(
            "ELASTICSEARCH_INDEX must start with a lowercase letter or digit "
            "and contain only lowercase letters, digits, underscores or hyphens."
        )
    return value


def _headers(*, ndjson: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-ndjson" if ndjson else "application/json",
    }
    if config.elasticsearch_api_key:
        headers["Authorization"] = f"ApiKey {config.elasticsearch_api_key}"
    elif config.elasticsearch_username and config.elasticsearch_password:
        raw = (
            f"{config.elasticsearch_username}:{config.elasticsearch_password}"
        ).encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    return headers


def _request(
    method: str,
    path: str,
    *,
    payload: Any | None = None,
    ndjson: str | None = None,
    expected: tuple[int, ...] = (200, 201),
    allow_404: bool = False,
) -> Any | None:
    if payload is not None and ndjson is not None:
        raise ValueError("payload and ndjson are mutually exclusive")
    body: bytes | None = None
    if payload is not None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=_json_default,
        ).encode("utf-8")
    elif ndjson is not None:
        body = ndjson.encode("utf-8")
    request = urllib.request.Request(
        config.elasticsearch_url + path,
        data=body,
        headers=_headers(ndjson=ndjson is not None),
        method=method,
    )
    try:
        with urllib.request.urlopen(
            request, timeout=config.elasticsearch_timeout_seconds
        ) as response:
            raw = response.read()
            if response.status not in expected:
                raise SearchEngineError(
                    f"Elasticsearch returned HTTP {response.status} for {method} {path}."
                )
            if not raw:
                return {}
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SearchEngineError(
                    f"Elasticsearch returned invalid JSON for {method} {path}."
                ) from exc
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if allow_404 and exc.code == 404:
            return None
        message = raw[:1000] if raw else str(exc.reason)
        raise SearchEngineError(
            f"Elasticsearch HTTP {exc.code} for {method} {path}: {message}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SearchEngineError(
            f"Elasticsearch is unavailable for {method} {path}: {exc}"
        ) from exc


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def ping() -> bool:
    if not config.elasticsearch_enabled:
        return True
    try:
        result = _request("GET", "/", expected=(200,))
        return isinstance(result, dict)
    except SearchEngineError:
        logger.exception("Elasticsearch ping failed")
        return False


@contextlib.contextmanager
def _exclusive_index_lock() -> Generator[Any, None, None]:
    """Serialize index creation/rebuilds across API and worker processes.

    A PostgreSQL session advisory lock is used because PostgreSQL is always the
    source of truth and is already a required dependency. This avoids a race in
    which two startup processes could attach the alias to different concrete
    indices. The lock connection is kept in autocommit mode so no long-running
    database transaction is held while Elasticsearch performs network I/O.
    """
    with database.connection() as conn:
        previous_autocommit = conn.autocommit
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                
                
                cur.execute(
                    "SELECT set_config('statement_timeout','0',false)"
                )
                cur.execute("SELECT pg_advisory_lock(74185, 2963)")
                cur.execute(
                    "SELECT set_config('statement_timeout',%s,false)",
                    (f"{config.db_statement_timeout_ms}ms",),
                )
            yield conn
        finally:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(74185, 2963)")
            finally:
                conn.autocommit = previous_autocommit


def _mapping() -> dict[str, Any]:
    text_with_raw = {
        "type": "text",
        "fields": {
            "raw": {"type": "keyword", "normalizer": "lowercase_normalizer"}
        },
    }
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "max_result_window": 100000,
            "analysis": {
                "normalizer": {
                    "lowercase_normalizer": {
                        "type": "custom",
                        "filter": ["lowercase"],
                    }
                }
            },
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "ticket_id": {"type": "long"},
                "match_id": {"type": "long"},
                "sport_code": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer",
                },
                "sport_name": text_with_raw,
                "sport_is_active": {"type": "boolean"},
                "home_team": text_with_raw,
                "home_team_is_active": {"type": "boolean"},
                "away_team": text_with_raw,
                "away_team_is_active": {"type": "boolean"},
                "tournament_name": text_with_raw,
                "starts_at": {"type": "date"},
                "ends_at": {"type": "date"},
                "match_status": {"type": "keyword"},
                "match_is_active": {"type": "boolean"},
                "organizer_id": {"type": "long"},
                "organizer_name": text_with_raw,
                "organizer_is_active": {"type": "boolean"},
                "venue_id": {"type": "long"},
                "venue_name": text_with_raw,
                "venue_is_active": {"type": "boolean"},
                "city_id": {"type": "long"},
                "city_name": text_with_raw,
                "province_name": text_with_raw,
                "category_code": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer",
                },
                "category_name": text_with_raw,
                "category_is_active": {"type": "boolean"},
                "section_code": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer",
                },
                "row_code": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer",
                },
                "seat_code": {
                    "type": "keyword",
                    "normalizer": "lowercase_normalizer",
                },
                "is_numbered": {"type": "boolean"},
                "price": {"type": "scaled_float", "scaling_factor": 100},
                "total_capacity": {"type": "integer"},
                "held_quantity": {"type": "integer"},
                "sold_quantity": {"type": "integer"},
                "change_held_quantity": {"type": "integer"},
                "available_quantity": {"type": "integer"},
                "sale_starts_at": {"type": "date"},
                "sale_ends_at": {"type": "date"},
                "is_active": {"type": "boolean"},
                "amenities": text_with_raw,
            },
        },
    }


def alias_exists() -> bool:
    alias = urllib.parse.quote(_index_alias(), safe="")
    return (
        _request(
            "HEAD", f"/_alias/{alias}", expected=(200,), allow_404=True
        )
        is not None
    )


def index_ready() -> bool:
    """Return whether the enabled search service and public alias are usable."""
    if not config.elasticsearch_enabled:
        return True
    try:
        return ping() and alias_exists()
    except SearchEngineError:
        logger.exception("Elasticsearch index readiness check failed")
        return False


def ensure_index() -> None:
    """Ensure a complete public index exists; never expose an empty bootstrap."""
    if not alias_exists():
        full_sync(only_if_missing=True)


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: (
            _json_default(value)
            if isinstance(value, (Decimal, datetime, date, uuid.UUID))
            else value
        )
        for key, value in row.items()
    }


def _bulk_index(index_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    lines: list[str] = []
    for row in rows:
        ticket_id = int(row["ticket_id"])
        lines.append(
            json.dumps(
                {"index": {"_index": index_name, "_id": str(ticket_id)}},
                separators=(",", ":"),
            )
        )
        lines.append(
            json.dumps(
                _document(row),
                ensure_ascii=False,
                separators=(",", ":"),
                default=_json_default,
            )
        )
    response = _request(
        "POST",
        "/_bulk",
        ndjson="\n".join(lines) + "\n",
        expected=(200,),
    )
    if not isinstance(response, dict) or response.get("errors"):
        failures: list[Any] = []
        if isinstance(response, dict):
            for item in response.get("items", []):
                result = item.get("index", {}) if isinstance(item, dict) else {}
                if result.get("error"):
                    failures.append(result.get("error"))
                    if len(failures) >= 5:
                        break
        raise SearchEngineError(f"Elasticsearch bulk indexing failed: {failures}")


def full_sync(*, only_if_missing: bool = False) -> int:
    """Build a fresh index and atomically swap the public alias.

    ``only_if_missing`` is used by the worker's startup path. It prevents a
    duplicate rebuild when the API container is already performing the initial
    synchronization under the same advisory lock.
    """
    with _exclusive_index_lock() as conn:
        if only_if_missing and alias_exists():
            return 0

        alias_name = _index_alias()
        concrete_name = (
            f"{alias_name}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-"
            f"{uuid.uuid4().hex[:8]}"
        )
        concrete = urllib.parse.quote(concrete_name, safe="")
        _request("PUT", f"/{concrete}", payload=_mapping(), expected=(200,))
        try:
            indexed = 0
            last_ticket_id = 0
            batch_size = config.elasticsearch_sync_batch_size
            while True:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT *
                        FROM v_ticket_catalog
                        WHERE ticket_id>%s
                        ORDER BY ticket_id
                        LIMIT %s
                        """,
                        (last_ticket_id, batch_size),
                    )
                    rows = list(cur.fetchall())
                if not rows:
                    break
                _bulk_index(concrete_name, rows)
                indexed += len(rows)
                last_ticket_id = int(rows[-1]["ticket_id"])

            _request("POST", f"/{concrete}/_refresh", expected=(200,))
            old = _request(
                "GET",
                f"/_alias/{urllib.parse.quote(alias_name, safe='')}",
                expected=(200,),
                allow_404=True,
            )
            old_indices = list(old) if isinstance(old, dict) else []
            actions: list[dict[str, Any]] = [
                {"remove": {"index": name, "alias": alias_name}}
                for name in old_indices
                if name != concrete_name
            ]
            actions.append(
                {"add": {"index": concrete_name, "alias": alias_name}}
            )
            _request(
                "POST", "/_aliases", payload={"actions": actions}, expected=(200,)
            )
            for name in old_indices:
                if name != concrete_name and name.startswith(alias_name + "-"):
                    try:
                        _request(
                            "DELETE",
                            "/" + urllib.parse.quote(name, safe=""),
                            expected=(200,),
                            allow_404=True,
                        )
                    except SearchEngineError:
                        logger.exception(
                            "Could not delete obsolete search index %s", name
                        )
            return indexed
        except Exception:
            try:
                _request(
                    "DELETE", f"/{concrete}", expected=(200,), allow_404=True
                )
            except SearchEngineError:
                logger.exception(
                    "Could not remove failed search index %s", concrete_name
                )
            raise


def sync_ticket(ticket_id: int) -> str:
    """Upsert or delete one ticket document based on current PostgreSQL state."""
    ensure_index()
    alias = urllib.parse.quote(_index_alias(), safe="")
    doc_id = urllib.parse.quote(str(ticket_id), safe="")
    row = database.fetch_one(
        "SELECT * FROM v_ticket_catalog WHERE ticket_id=%s", (ticket_id,)
    )
    if row is None:
        _request(
            "DELETE",
            f"/{alias}/_doc/{doc_id}?refresh=wait_for",
            expected=(200,),
            allow_404=True,
        )
        return "deleted"
    _request(
        "PUT",
        f"/{alias}/_doc/{doc_id}?refresh=wait_for",
        payload=_document(row),
        expected=(200, 201),
    )
    return "indexed"


def process_outbox(limit: int | None = None) -> int:
    """Claim and process transactional search-sync outbox rows safely."""
    if not config.elasticsearch_enabled:
        return 0
    batch_size = limit or config.elasticsearch_outbox_batch_size
    worker_id = uuid.uuid4().hex
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH candidates AS (
                SELECT id
                FROM search_sync_outbox
                WHERE processed_at IS NULL
                  AND available_at<=CURRENT_TIMESTAMP
                  AND (locked_at IS NULL OR locked_at<CURRENT_TIMESTAMP-INTERVAL '5 minutes')
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            UPDATE search_sync_outbox o
            SET locked_at=CURRENT_TIMESTAMP,locked_by=%s
            FROM candidates c
            WHERE o.id=c.id
            RETURNING o.id,o.ticket_id,o.revision
            """,
            (batch_size, worker_id),
        )
        claimed = list(cur.fetchall())

    processed = 0
    for item in claimed:
        outbox_id = int(item["id"])
        ticket_id = int(item["ticket_id"])
        revision = int(item["revision"])
        try:
            sync_ticket(ticket_id)
            with database.transaction() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE search_sync_outbox
                    SET processed_at=CURRENT_TIMESTAMP,locked_at=NULL,locked_by=NULL,
                        last_error=NULL
                    WHERE id=%s AND revision=%s AND locked_by=%s
                    """,
                    (outbox_id, revision, worker_id),
                )
                if cur.rowcount:
                    processed += 1
                else:
                    
                    
                    
                    cur.execute(
                        """
                        UPDATE search_sync_outbox
                        SET locked_at=NULL,locked_by=NULL
                        WHERE id=%s AND locked_by=%s
                        """,
                        (outbox_id, worker_id),
                    )
        except Exception as exc:
            logger.exception(
                "Search outbox sync failed outbox_id=%s ticket_id=%s",
                outbox_id,
                ticket_id,
            )
            with database.transaction() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE search_sync_outbox
                    SET attempts=attempts+1,
                        available_at=CURRENT_TIMESTAMP
                            + LEAST(3600,POWER(2,LEAST(attempts,10))) * INTERVAL '1 second',
                        locked_at=NULL,locked_by=NULL,last_error=%s
                    WHERE id=%s AND locked_by=%s
                    """,
                    (str(exc)[:2000], outbox_id, worker_id),
                )
    return processed


def cleanup_outbox() -> int:
    """Delete old successfully processed outbox rows after the retention window."""
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM search_sync_outbox
            WHERE processed_at IS NOT NULL
              AND processed_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
            """,
            (config.elasticsearch_outbox_retention_days,),
        )
        return int(cur.rowcount)


def _text_query(value: str, fields: list[str]) -> dict[str, Any]:
    return {
        "bool": {
            "should": [
                {
                    "multi_match": {
                        "query": value,
                        "fields": fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                },
                {
                    "multi_match": {
                        "query": value,
                        "fields": fields,
                        "type": "phrase_prefix",
                    }
                },
            ],
            "minimum_should_match": 1,
        }
    }


def search_tickets(
    filters: Mapping[str, Any], *, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    """Execute the public ticket search against the Elasticsearch alias."""
    if not alias_exists():
        raise SearchEngineError(
            "Elasticsearch ticket alias is not initialized; run a full sync."
        )
    filter_queries: list[dict[str, Any]] = [
        {"term": {"is_active": True}},
        {"term": {"match_is_active": True}},
        {"term": {"sport_is_active": True}},
        {"term": {"home_team_is_active": True}},
        {"term": {"away_team_is_active": True}},
        {"term": {"organizer_is_active": True}},
        {"term": {"venue_is_active": True}},
        {"term": {"category_is_active": True}},
        {"terms": {"match_status": ["scheduled", "postponed"]}},
        {"range": {"starts_at": {"gt": "now"}}},
        {"range": {"available_quantity": {"gt": 0}}},
        {
            "bool": {
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "sale_starts_at"}}}},
                    {"range": {"sale_starts_at": {"lte": "now"}}},
                ],
                "minimum_should_match": 1,
            }
        },
        {
            "bool": {
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "sale_ends_at"}}}},
                    {"range": {"sale_ends_at": {"gt": "now"}}},
                ],
                "minimum_should_match": 1,
            }
        },
    ]
    must_queries: list[dict[str, Any]] = []

    if filters.get("q"):
        must_queries.append(
            _text_query(
                str(filters["q"]),
                [
                    "home_team^3",
                    "away_team^3",
                    "tournament_name^2",
                    "venue_name^2",
                    "category_name",
                    "city_name",
                    "province_name",
                    "amenities",
                ],
            )
        )
    if filters.get("team"):
        must_queries.append(
            _text_query(str(filters["team"]), ["home_team^2", "away_team^2"])
        )
    if filters.get("sport"):
        value = str(filters["sport"])
        filter_queries.append(
            {
                "bool": {
                    "should": [
                        {"term": {"sport_code": value.lower()}},
                        {"term": {"sport_name.raw": value.lower()}},
                        {"match_phrase": {"sport_name": value}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )
    if filters.get("category"):
        value = str(filters["category"])
        filter_queries.append(
            {
                "bool": {
                    "should": [
                        {"term": {"category_code": value.lower()}},
                        {"term": {"category_name.raw": value.lower()}},
                        {"match_phrase": {"category_name": value}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )
    if filters.get("section"):
        filter_queries.append(
            {"term": {"section_code": str(filters["section"]).lower()}}
        )
    for field in ("city_id", "venue_id", "is_numbered"):
        source = "numbered" if field == "is_numbered" else field
        if filters.get(source) is not None:
            filter_queries.append({"term": {field: filters[source]}})
    if filters.get("date_from") is not None or filters.get("date_to") is not None:
        range_value: dict[str, Any] = {}
        if filters.get("date_from") is not None:
            range_value["gte"] = _json_default(filters["date_from"])
        if filters.get("date_to") is not None:
            range_value["lte"] = _json_default(filters["date_to"])
        filter_queries.append({"range": {"starts_at": range_value}})
    if filters.get("price_min") is not None or filters.get("price_max") is not None:
        range_value = {}
        if filters.get("price_min") is not None:
            range_value["gte"] = str(filters["price_min"])
        if filters.get("price_max") is not None:
            range_value["lte"] = str(filters["price_max"])
        filter_queries.append({"range": {"price": range_value}})
    if filters.get("min_available") is not None:
        filter_queries.append(
            {
                "range": {
                    "available_quantity": {"gte": int(filters["min_available"])}
                }
            }
        )

    order_map: dict[str, list[Any]] = {
        "starts_at": [{"starts_at": "asc"}, {"ticket_id": "asc"}],
        "-starts_at": [{"starts_at": "desc"}, {"ticket_id": "desc"}],
        "price": [{"price": "asc"}, {"starts_at": "asc"}],
        "-price": [{"price": "desc"}, {"starts_at": "asc"}],
        "demand": [{"sold_quantity": "desc"}, {"starts_at": "asc"}],
        "availability": [
            {"available_quantity": "desc"},
            {"starts_at": "asc"},
        ],
    }
    ordering = str(filters.get("ordering") or "starts_at")
    if ordering not in order_map:
        raise SearchEngineError(f"Unsupported ordering value: {ordering}")
    offset = (page - 1) * page_size
    if offset + page_size > 100000:
        raise SearchEngineError(
            "Elasticsearch result window exceeded 100000 records. Narrow the filters."
        )
    source_fields = [
        "ticket_id",
        "match_id",
        "sport_code",
        "sport_name",
        "home_team",
        "away_team",
        "tournament_name",
        "starts_at",
        "venue_id",
        "venue_name",
        "city_id",
        "city_name",
        "province_name",
        "category_code",
        "category_name",
        "section_code",
        "row_code",
        "seat_code",
        "is_numbered",
        "price",
        "available_quantity",
        "total_capacity",
        "sold_quantity",
        "amenities",
    ]
    payload = {
        "from": offset,
        "size": page_size,
        "track_total_hits": True,
        "_source": source_fields,
        "query": {"bool": {"filter": filter_queries, "must": must_queries}},
        "sort": order_map[ordering],
    }
    response = _request(
        "POST",
        f"/{urllib.parse.quote(_index_alias(), safe='')}/_search",
        payload=payload,
        expected=(200,),
    )
    if not isinstance(response, dict):
        raise SearchEngineError("Elasticsearch returned an empty search response.")
    hits = response.get("hits", {})
    total_value = hits.get("total", 0) if isinstance(hits, dict) else 0
    total = (
        int(total_value.get("value", 0))
        if isinstance(total_value, dict)
        else int(total_value or 0)
    )
    items = [
        dict(item.get("_source") or {})
        for item in hits.get("hits", [])
        if isinstance(item, dict)
    ]
    return items, total
