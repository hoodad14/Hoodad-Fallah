"""Consistent JSON response and serialization helpers."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.http import JsonResponse


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    return str(value)


def ok(data: Any = None, *, status: int = 200, meta: dict[str, Any] | None = None) -> JsonResponse:
    body: dict[str, Any] = {"success": True, "data": jsonable(data)}
    if meta is not None:
        body["meta"] = jsonable(meta)
    return JsonResponse(body, status=status, json_dumps_params={"ensure_ascii": False})


def error(
    code: str,
    message: str,
    *,
    status: int = 400,
    details: Any = None,
    request_id: str | None = None,
) -> JsonResponse:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = jsonable(details)
    if request_id:
        payload["request_id"] = request_id
    return JsonResponse(
        {"success": False, "error": payload},
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )
