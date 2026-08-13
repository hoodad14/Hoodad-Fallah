"""Catalog, lookup, search, and ticket-detail services."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Mapping

import cache
import database
import search_engine
from config import config
from exceptions import ApiError, NotFound

logger = logging.getLogger(__name__)


def _cached_lookup(key: str, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    version = cache.version("lookups")
    cache_key = f"lookup:v{version}:{key}"
    if (result := cache.get_json(cache_key)) is not None:
        return result
    result = database.fetch_all(query, params)
    cache.set_json(cache_key, result, config.cache_default_seconds)
    return result


def cities() -> list[dict[str, Any]]:
    return _cached_lookup(
        "cities",
        """
        SELECT c.id,c.name,p.id AS province_id,p.name AS province_name
        FROM cities c JOIN provinces p ON p.id=c.province_id
        ORDER BY p.name,c.name
        """,
    )


def venues(city_id: int | None = None) -> list[dict[str, Any]]:
    key = f"venues:{city_id or 'all'}"
    return _cached_lookup(
        key,
        """
        SELECT v.id,v.name,v.address,v.capacity,v.latitude,v.longitude,
               c.id AS city_id,c.name AS city_name,p.name AS province_name
        FROM venues v
        JOIN cities c ON c.id=v.city_id
        JOIN provinces p ON p.id=c.province_id
        WHERE v.is_active AND (%s::bigint IS NULL OR v.city_id=%s)
        ORDER BY c.name,v.name
        """,
        (city_id, city_id),
    )


def sports() -> list[dict[str, Any]]:
    return _cached_lookup(
        "sports",
        "SELECT id,code,name FROM sport_types WHERE is_active ORDER BY name",
    )


def ticket_categories() -> list[dict[str, Any]]:
    return _cached_lookup(
        "ticket-categories",
        "SELECT id,code,name,sort_order FROM ticket_categories WHERE is_active ORDER BY sort_order,name",
    )


def payment_methods() -> list[dict[str, Any]]:
    return _cached_lookup(
        "payment-methods",
        "SELECT id,code,name FROM payment_methods WHERE is_active ORDER BY id",
    )


def report_categories() -> list[dict[str, Any]]:
    return _cached_lookup(
        "report-categories",
        "SELECT id,code,name FROM report_categories ORDER BY name",
    )


def _search_tickets_sql(
    filters: Mapping[str, Any], *, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    clauses = [
        "is_active",
        "match_is_active",
        "sport_is_active",
        "home_team_is_active",
        "away_team_is_active",
        "organizer_is_active",
        "venue_is_active",
        "category_is_active",
        "match_status IN ('scheduled','postponed')",
        "starts_at > CURRENT_TIMESTAMP",
        "available_quantity > 0",
        "(sale_starts_at IS NULL OR sale_starts_at <= CURRENT_TIMESTAMP)",
        "(sale_ends_at IS NULL OR sale_ends_at > CURRENT_TIMESTAMP)",
    ]
    params: list[Any] = []

    def add(condition: str, value: Any, *, twice: bool = False) -> None:
        clauses.append(condition)
        params.append(value)
        if twice:
            params.append(value)

    if filters.get("sport"):
        clauses.append("(lower(sport_code)=lower(%s) OR lower(sport_name)=lower(%s))")
        params.extend([filters["sport"], filters["sport"]])
    if filters.get("city_id"):
        add("city_id=%s", filters["city_id"])
    if filters.get("venue_id"):
        add("venue_id=%s", filters["venue_id"])
    if filters.get("category"):
        clauses.append("(lower(category_code)=lower(%s) OR lower(category_name)=lower(%s))")
        params.extend([filters["category"], filters["category"]])
    if filters.get("section"):
        add("lower(section_code)=lower(%s)", filters["section"])
    if filters.get("team"):
        clauses.append("(home_team ILIKE %s OR away_team ILIKE %s)")
        term = f"%{filters['team']}%"
        params.extend([term, term])
    if filters.get("q"):
        term = f"%{filters['q']}%"
        clauses.append(
            "(home_team ILIKE %s OR away_team ILIKE %s OR venue_name ILIKE %s "
            "OR tournament_name ILIKE %s OR category_name ILIKE %s "
            "OR city_name ILIKE %s OR province_name ILIKE %s "
            "OR sport_name ILIKE %s OR amenities ILIKE %s)"
        )
        params.extend([term] * 9)
    if filters.get("date_from"):
        add("starts_at >= %s", filters["date_from"])
    if filters.get("date_to"):
        add("starts_at <= %s", filters["date_to"])
    if filters.get("price_min") is not None:
        add("price >= %s", filters["price_min"])
    if filters.get("price_max") is not None:
        add("price <= %s", filters["price_max"])
    if filters.get("min_available") is not None:
        add("available_quantity >= %s", filters["min_available"])
    if filters.get("numbered") is not None:
        add("is_numbered=%s", filters["numbered"])

    ordering = filters.get("ordering", "starts_at")
    order_map = {
        "starts_at": "starts_at ASC, ticket_id ASC",
        "-starts_at": "starts_at DESC, ticket_id DESC",
        "price": "price ASC, starts_at ASC",
        "-price": "price DESC, starts_at ASC",
        "demand": "sold_quantity DESC, starts_at ASC",
        "availability": "available_quantity DESC, starts_at ASC",
    }
    if ordering not in order_map:
        raise ApiError("validation_error", "Unsupported ordering value.", 422)

    where = " AND ".join(clauses)
    normalized = "&".join(f"{k}={filters[k]}" for k in sorted(filters) if filters[k] is not None)
    cache_key = (
        f"ticket-search:v{cache.version('tickets')}:p{page}:s{page_size}:"
        f"{cache.fingerprint(normalized)}"
    )
    if (cached := cache.get_json(cache_key)) is not None:
        return cached["items"], int(cached["total"])

    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM v_ticket_catalog WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT ticket_id,match_id,sport_code,sport_name,home_team,away_team,
                   tournament_name,starts_at,venue_id,venue_name,city_id,city_name,
                   province_name,category_code,category_name,section_code,row_code,
                   seat_code,is_numbered,price,available_quantity,total_capacity,
                   sold_quantity,amenities
            FROM v_ticket_catalog
            WHERE {where}
            ORDER BY {order_map[ordering]}
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        items = list(cur.fetchall())
    cache.set_json(cache_key, {"items": items, "total": total}, config.cache_ticket_seconds)
    return items, total


def search_tickets(
    filters: Mapping[str, Any], *, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    """Search with Elasticsearch when enabled, otherwise use PostgreSQL.

    The Redis versioned cache is shared conceptually but keyed by backend, so a
    fallback result can never be confused with an Elasticsearch result.
    """
    if not config.elasticsearch_enabled:
        return _search_tickets_sql(filters, page=page, page_size=page_size)

    normalized = "&".join(
        f"{key}={filters[key]}"
        for key in sorted(filters)
        if filters[key] is not None
    )
    cache_key = (
        f"ticket-search:es:v{cache.version('tickets')}:p{page}:s{page_size}:"
        f"{cache.fingerprint(normalized)}"
    )
    if (cached := cache.get_json(cache_key)) is not None:
        return cached["items"], int(cached["total"])
    try:
        items, total = search_engine.search_tickets(
            filters, page=page, page_size=page_size
        )
    except search_engine.SearchEngineError as exc:
        logger.exception("Elasticsearch ticket search failed")
        if not config.elasticsearch_fallback_to_sql:
            raise ApiError(
                "search_unavailable",
                "Ticket search is temporarily unavailable.",
                503,
                {"backend": "elasticsearch"},
            ) from exc
        return _search_tickets_sql(filters, page=page, page_size=page_size)
    cache.set_json(
        cache_key,
        {"items": items, "total": total},
        config.cache_ticket_seconds,
    )
    return items, total


def ticket_detail(ticket_id: int, *, include_inactive: bool = False) -> dict[str, Any]:
    visibility = "support" if include_inactive else "public"
    key = f"ticket-detail:{visibility}:v{cache.version('tickets')}:{ticket_id}"
    if (cached := cache.get_json(key)) is not None:
        return cached
    row = database.fetch_one(
        """
        SELECT vc.*,
               COALESCE(
                 (SELECT jsonb_agg(jsonb_build_object(
                     'id',a.id,'code',a.code,'name',a.name,
                     'description',a.description,'details',ta.details
                 ) ORDER BY a.name)
                  FROM ticket_amenities ta
                  JOIN amenities a ON a.id=ta.amenity_id
                  WHERE ta.ticket_id=vc.ticket_id),
                 '[]'::jsonb
               ) AS amenity_details
        FROM v_ticket_catalog vc
        WHERE vc.ticket_id=%s
          AND (
              %s=TRUE
              OR (
                  vc.is_active
                  AND vc.match_is_active
                  AND vc.sport_is_active
                  AND vc.home_team_is_active
                  AND vc.away_team_is_active
                  AND vc.organizer_is_active
                  AND vc.venue_is_active
                  AND vc.category_is_active
                  AND vc.match_status IN ('scheduled','postponed')
                  AND vc.starts_at>CURRENT_TIMESTAMP
              )
          )
        """,
        (ticket_id, include_inactive),
    )
    if not row:
        raise NotFound("Ticket not found or no longer publicly available.")
    cache.set_json(key, row, config.cache_ticket_seconds)
    return row


def seat_change_options(user_id: int, reservation_id: int) -> list[dict[str, Any]]:
    ownership = database.fetch_one(
        "SELECT id FROM reservations WHERE id=%s AND user_id=%s AND status IN ('held','paid')",
        (reservation_id, user_id),
    )
    if not ownership:
        raise NotFound("Eligible reservation not found.")
    return database.fetch_all(
        """
        SELECT candidate.ticket_id,candidate.category_name,candidate.section_code,
               candidate.row_code,candidate.seat_code,candidate.is_numbered,
               candidate.price,candidate.available_quantity,candidate.amenities
        FROM reservations r
        JOIN tickets current_ticket ON current_ticket.id=r.ticket_id
        JOIN v_ticket_catalog candidate ON candidate.match_id=current_ticket.match_id
        WHERE r.id=%s
          AND candidate.ticket_id<>r.ticket_id
          AND candidate.price=r.unit_price
          AND candidate.available_quantity>=r.quantity
          AND candidate.is_active
          AND candidate.match_is_active
          AND candidate.sport_is_active
          AND candidate.home_team_is_active
          AND candidate.away_team_is_active
          AND candidate.organizer_is_active
          AND candidate.venue_is_active
          AND candidate.category_is_active
          AND candidate.match_status IN ('scheduled','postponed')
          AND candidate.starts_at>CURRENT_TIMESTAMP
          AND (candidate.sale_starts_at IS NULL OR candidate.sale_starts_at<=CURRENT_TIMESTAMP)
          AND (candidate.sale_ends_at IS NULL OR candidate.sale_ends_at>CURRENT_TIMESTAMP)
        ORDER BY candidate.category_name,candidate.section_code,candidate.row_code,candidate.seat_code
        """,
        (reservation_id,),
    )


def invalidate_ticket_cache() -> None:
    cache.bump_version("tickets")
    cache.bump_version("lookups")


def amenities() -> list[dict[str, Any]]:
    return _cached_lookup(
        "amenities",
        "SELECT id,code,name,description FROM amenities ORDER BY name",
    )


def matches(*, upcoming_only: bool = True) -> list[dict[str, Any]]:
    return _cached_lookup(
        f"matches:{'upcoming' if upcoming_only else 'all'}",
        """
        SELECT m.id,st.code AS sport_code,st.name AS sport_name,
               ht.name AS home_team,at.name AS away_team,m.tournament_name,
               m.starts_at,m.ends_at,m.status,m.is_active,
               v.id AS venue_id,v.name AS venue_name,c.name AS city_name,
               o.id AS organizer_id,o.name AS organizer_name
        FROM matches m
        JOIN sport_types st ON st.id=m.sport_type_id
        JOIN teams ht ON ht.id=m.home_team_id
        JOIN teams at ON at.id=m.away_team_id
        JOIN venues v ON v.id=m.venue_id
        JOIN cities c ON c.id=v.city_id
        JOIN organizers o ON o.id=m.organizer_id
        WHERE m.is_active
          AND st.is_active
          AND ht.is_active
          AND at.is_active
          AND v.is_active
          AND o.is_active
          AND m.status IN ('scheduled','postponed')
          AND (%s=FALSE OR m.starts_at>CURRENT_TIMESTAMP)
        ORDER BY m.starts_at,m.id
        """,
        (upcoming_only,),
    )
