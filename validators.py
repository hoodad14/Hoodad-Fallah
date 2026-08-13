"""Strict input parsing helpers."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import RequestDataTooBig
from django.http import HttpRequest
from django.utils.dateparse import parse_date, parse_datetime

from exceptions import ApiError

EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.I)
PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$")
_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ApiError("invalid_json", f"Duplicate JSON key: {key}.", 400)
        result[key] = value
    return result


def body(request: HttpRequest) -> dict[str, Any]:
    content_type = request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ApiError("unsupported_media_type", "Content-Type must be application/json.", 415)
    try:
        raw = request.body
    except RequestDataTooBig as exc:
        raise ApiError("payload_too_large", "Request body is too large.", 413) from exc
    if not raw:
        return {}
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_without_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError("invalid_json", "Request body is not valid JSON.", 400) from exc
    if not isinstance(value, dict):
        raise ApiError("invalid_json", "JSON body must be an object.", 400)
    return value


def required(data: dict[str, Any], name: str) -> Any:
    value = data.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ApiError("validation_error", f"{name} is required.", 422, {"field": name})
    return value


def text(value: Any, name: str, *, min_len: int = 0, max_len: int = 1000, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str):
        raise ApiError("validation_error", f"{name} must be a string.", 422, {"field": name})
    value = value.strip()
    if len(value) < min_len or len(value) > max_len:
        raise ApiError("validation_error", f"{name} length must be between {min_len} and {max_len}.", 422, {"field": name})
    return value


def integer(value: Any, name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        raise ApiError("validation_error", f"{name} must be an integer.", 422)
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError("validation_error", f"{name} must be an integer.", 422) from exc
    if minimum is not None and result < minimum:
        raise ApiError("validation_error", f"{name} must be at least {minimum}.", 422)
    if maximum is not None and result > maximum:
        raise ApiError("validation_error", f"{name} must be at most {maximum}.", 422)
    return result


def decimal_number(value: Any, name: str, *, minimum: Decimal | None = None, maximum: Decimal | None = None) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ApiError("validation_error", f"{name} must be a decimal number.", 422) from exc
    if not result.is_finite():
        raise ApiError("validation_error", f"{name} must be finite.", 422)
    if minimum is not None and result < minimum:
        raise ApiError("validation_error", f"{name} must be at least {minimum}.", 422)
    if maximum is not None and result > maximum:
        raise ApiError("validation_error", f"{name} must be at most {maximum}.", 422)
    return result


def boolean(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ApiError("validation_error", f"{name} must be boolean.", 422)


def email(value: Any, name: str = "email", *, allow_none: bool = False) -> str | None:
    value = text(value, name, min_len=3, max_len=254, allow_none=allow_none)
    if value is None:
        return None
    value = value.lower()
    if not EMAIL_RE.fullmatch(value):
        raise ApiError("validation_error", f"{name} is not a valid email address.", 422)
    return value


def phone(value: Any, name: str = "phone", *, allow_none: bool = False) -> str | None:
    value = text(value, name, min_len=10, max_len=32, allow_none=allow_none)
    if value is None:
        return None
    value = value.translate(_DIGIT_TRANSLATION)
    value = re.sub(r"[\s()\-]", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]
    if not PHONE_RE.fullmatch(value):
        raise ApiError("validation_error", f"{name} is not a valid phone number.", 422)
    return value


def password(value: Any, name: str = "password") -> str:
    value = text(value, name, min_len=8, max_len=128)
    assert value is not None
    if not PASSWORD_RE.fullmatch(value):
        raise ApiError(
            "validation_error",
            f"{name} must contain at least one uppercase letter, one lowercase letter, and one digit.",
            422,
        )
    return value


def date_value(value: Any, name: str, *, allow_none: bool = False) -> date | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not (parsed := parse_date(value)):
        raise ApiError("validation_error", f"{name} must use YYYY-MM-DD format.", 422)
    return parsed


def datetime_value(value: Any, name: str, *, allow_none: bool = False) -> datetime | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not (parsed := parse_datetime(value)):
        raise ApiError("validation_error", f"{name} must be an ISO-8601 datetime.", 422)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApiError("validation_error", f"{name} must include a timezone offset.", 422)
    return parsed


def url(value: Any, name: str = "url", *, allow_none: bool = False) -> str | None:
    """Validate an absolute HTTP(S) URL suitable for a public profile image."""
    from urllib.parse import urlsplit

    value = text(value, name, min_len=1, max_len=2000, allow_none=allow_none)
    if value is None:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ApiError(
            "validation_error",
            f"{name} must be an absolute HTTP or HTTPS URL.",
            422,
            {"field": name},
        )
    if parsed.username or parsed.password:
        raise ApiError(
            "validation_error",
            f"{name} must not contain embedded credentials.",
            422,
            {"field": name},
        )
    return value


def optional_query_text(
    value: Any, name: str, *, max_len: int = 200
) -> str | None:
    if value in (None, ""):
        return None
    return text(value, name, min_len=1, max_len=max_len)


def ensure_allowed_fields(data: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ApiError(
            "validation_error",
            "Unknown request field(s) were supplied.",
            422,
            {"unknown_fields": unknown},
        )
    return data

def ensure_allowed_query_params(request: HttpRequest, allowed: set[str]) -> None:
    """Reject undocumented or repeated query-string parameters.

    Repeated keys are rejected because every current ArenaPass endpoint defines
    scalar query parameters. This avoids ambiguous parsing differences between
    clients, proxies and application code.
    """
    unknown = sorted(set(request.GET.keys()) - allowed)
    repeated = sorted(
        key for key, values in request.GET.lists() if len(values) > 1
    )
    if unknown or repeated:
        details: dict[str, Any] = {}
        if unknown:
            details["unknown_query_parameters"] = unknown
        if repeated:
            details["repeated_query_parameters"] = repeated
        raise ApiError(
            "validation_error",
            "Invalid query-string parameter(s) were supplied.",
            422,
            details,
        )

