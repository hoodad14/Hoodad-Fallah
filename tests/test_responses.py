from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from responses import jsonable


def test_jsonable_handles_database_types() -> None:
    value = {
        "decimal": Decimal("12.50"),
        "time": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "uuid": uuid4(),
    }
    result = jsonable(value)
    assert result["decimal"] == "12.50"
    assert result["time"].startswith("2026-01-01")
    assert isinstance(result["uuid"], str)
