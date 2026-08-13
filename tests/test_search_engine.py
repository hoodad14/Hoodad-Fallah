from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import search_engine


def test_search_mapping_is_strict_and_matches_catalog_contract() -> None:
    mapping = search_engine._mapping()  
    assert mapping["mappings"]["dynamic"] == "strict"
    properties = set(mapping["mappings"]["properties"])
    assert properties == {
        "ticket_id",
        "match_id",
        "sport_code",
        "sport_name",
        "sport_is_active",
        "home_team",
        "home_team_is_active",
        "away_team",
        "away_team_is_active",
        "tournament_name",
        "starts_at",
        "ends_at",
        "match_status",
        "match_is_active",
        "organizer_id",
        "organizer_name",
        "organizer_is_active",
        "venue_id",
        "venue_name",
        "venue_is_active",
        "city_id",
        "city_name",
        "province_name",
        "category_code",
        "category_name",
        "category_is_active",
        "section_code",
        "row_code",
        "seat_code",
        "is_numbered",
        "price",
        "total_capacity",
        "held_quantity",
        "sold_quantity",
        "change_held_quantity",
        "available_quantity",
        "sale_starts_at",
        "sale_ends_at",
        "is_active",
        "amenities",
    }


def test_search_builds_filtered_paginated_query(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(search_engine, "alias_exists", lambda: True)

    def fake_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(method=method, path=path, **kwargs)
        return {
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "hits": [{"_source": {"ticket_id": 7, "price": "1000.00"}}],
            }
        }

    monkeypatch.setattr(search_engine, "_request", fake_request)
    items, total = search_engine.search_tickets(
        {
            "q": "tehran",
            "team": "esteghlal",
            "sport": "football",
            "category": "vip",
            "section": "A",
            "city_id": 1,
            "venue_id": 2,
            "date_from": datetime(2026, 8, 1, tzinfo=timezone.utc),
            "date_to": datetime(2026, 9, 1, tzinfo=timezone.utc),
            "price_min": Decimal("100"),
            "price_max": Decimal("5000"),
            "min_available": 2,
            "numbered": False,
            "ordering": "demand",
        },
        page=2,
        page_size=25,
    )

    assert total == 1
    assert items == [{"ticket_id": 7, "price": "1000.00"}]
    assert captured["method"] == "POST"
    assert captured["path"].endswith("/_search")
    payload = captured["payload"]
    assert payload["from"] == 25
    assert payload["size"] == 25
    assert payload["track_total_hits"] is True
    assert payload["sort"][0] == {"sold_quantity": "desc"}
    serialized = str(payload)
    for expected in (
        "sport_code",
        "category_code",
        "section_code",
        "city_id",
        "venue_id",
        "starts_at",
        "price",
        "available_quantity",
        "is_numbered",
        "phrase_prefix",
    ):
        assert expected in serialized


def test_search_refuses_uninitialized_alias(monkeypatch: Any) -> None:
    monkeypatch.setattr(search_engine, "alias_exists", lambda: False)
    try:
        search_engine.search_tickets({}, page=1, page_size=20)
    except search_engine.SearchEngineError as exc:
        assert "full sync" in str(exc).lower()
    else:
        raise AssertionError("Search accepted a missing public index alias")
