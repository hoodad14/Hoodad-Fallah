from __future__ import annotations

import pytest
from django.test import RequestFactory

from exceptions import ApiError
from validators import (
    boolean,
    email,
    ensure_allowed_fields,
    ensure_allowed_query_params,
    integer,
    password,
    phone,
    url,
)


def test_email_normalizes_case() -> None:
    assert email("User.Name@Example.COM") == "user.name@example.com"


@pytest.mark.parametrize("value", ["bad", "a@b", "a b@example.com"])
def test_invalid_email_is_rejected(value: str) -> None:
    with pytest.raises(ApiError):
        email(value)


def test_phone_validation() -> None:
    assert phone("09121234567") == "09121234567"
    assert phone("+989121234567") == "+989121234567"
    with pytest.raises(ApiError):
        phone("12-ab")


def test_password_policy() -> None:
    assert password("StrongPass1") == "StrongPass1"
    with pytest.raises(ApiError):
        password("weakpass")


def test_integer_range_and_boolean_rejection() -> None:
    assert integer("10", "quantity", minimum=1, maximum=20) == 10
    with pytest.raises(ApiError):
        integer(0, "quantity", minimum=1)
    with pytest.raises(ApiError):
        integer(True, "quantity")


def test_boolean_parser_is_strict() -> None:
    assert boolean("true", "flag") is True
    assert boolean("false", "flag") is False
    with pytest.raises(ApiError):
        boolean("yes", "flag")


def test_http_url_validation() -> None:
    assert url("https://example.com/avatar.png", "avatar") == "https://example.com/avatar.png"
    with pytest.raises(ApiError):
        url("javascript:alert(1)", "avatar")
    with pytest.raises(ApiError):
        url("https://user:pass@example.com/private", "avatar")


def test_unknown_json_fields_are_rejected() -> None:
    assert ensure_allowed_fields({"name": "Ali"}, {"name"}) == {"name": "Ali"}
    with pytest.raises(ApiError) as exc:
        ensure_allowed_fields({"name": "Ali", "role": "support"}, {"name"})
    assert exc.value.code == "validation_error"

def test_unknown_and_repeated_query_parameters_are_rejected() -> None:
    factory = RequestFactory()
    request = factory.get("/api/v1/tickets?page=1&unexpected=yes")
    with pytest.raises(ApiError) as exc:
        ensure_allowed_query_params(request, {"page"})
    assert exc.value.details == {"unknown_query_parameters": ["unexpected"]}

    repeated = factory.get("/api/v1/tickets?page=1&page=2")
    with pytest.raises(ApiError) as exc:
        ensure_allowed_query_params(repeated, {"page"})
    assert exc.value.details == {"repeated_query_parameters": ["page"]}

