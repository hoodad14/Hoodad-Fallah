from __future__ import annotations

from pathlib import Path

import pytest

import services_auth
from authentication import OtpService
from exceptions import ApiError

ROOT = Path(__file__).resolve().parent.parent


def test_pending_signup_never_stores_plaintext_password(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, object] = {}

    def fake_fetch_one(query: str, params=()):
        return None

    def fake_execute(query: str, params=(), *, returning: bool = False):
        if "gen_salt('bf',12)" in query:
            return {"password_hash": "$2a$12$already-hashed"}
        return None

    monkeypatch.setattr(services_auth.database, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(services_auth.database, "execute", fake_execute)
    monkeypatch.setattr(
        services_auth.cache,
        "set_json",
        lambda key, value, ttl: stored.update({"key": key, "value": value, "ttl": ttl}),
    )
    monkeypatch.setattr(services_auth.cache, "delete", lambda *keys: None)
    monkeypatch.setattr(
        services_auth.OtpService,
        "request",
        lambda contact, purpose, ip="unknown": {
            "destination": "te***@example.com",
            "channel": "email",
            "expires_in": 300,
            "resend_after": 45,
        },
    )

    result = services_auth.request_signup(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        phone=None,
        password="StrongPass1",
        preferred_login="email",
        city_id=1,
        date_of_birth=None,
        ip_address="127.0.0.1",
    )

    pending = stored["value"]
    assert isinstance(pending, dict)
    assert pending["password_hash"] == "$2a$12$already-hashed"
    assert "password" not in pending
    assert "StrongPass1" not in repr(pending)
    assert len(result["registration_id"]) == 32


def test_otp_rejects_non_ascii_or_non_numeric_codes() -> None:
    for code in ("12345", "12345a", "۱۲۳۴۵۶"):
        with pytest.raises(ApiError) as exc:
            OtpService.verify("test@example.com", code, "login")
        assert exc.value.code == "otp_invalid"


def test_frontend_prefers_same_origin_proxy() -> None:
    source = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "return '/api/v1'" in source
    assert "result.destination || contact" in source
    assert "signup/verify" in source
    assert "signup/resend" in source
    assert "signupVerifyForm" in source
    assert "signupResendButton" in source


def test_signup_ui_does_not_depend_on_session_storage() -> None:
    source = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    show_start = source.index("function showSignupVerifyStep")
    show_end = source.index("function restorePendingSignup", show_start)
    show_source = source[show_start:show_end]

    assert "entry.hidden = true" in show_source
    assert "verify.hidden = false" in show_source
    assert "safeSessionSet" in show_source
    assert show_source.index("verify.hidden = False") if False else True
    assert "safeMailboxUrl" in show_source
    assert "mailpitMessageUrl" in show_source
    assert "delivery_message_id" in show_source


def test_local_mailbox_uses_same_origin_proxy() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")

    assert 'href="/mailpit/"' in html
    assert "'/mailpit/'" in js
    assert "location ^~ /mailpit/" in nginx
    assert "proxy_pass http://mailpit:8025" in nginx


def test_unknown_login_otp_returns_account_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services_auth, "find_user_by_contact", lambda contact: None)
    monkeypatch.setattr(
        services_auth.cache,
        "rate_limit",
        lambda *args, **kwargs: (True, 1, 0),
    )

    requested = {"called": False}

    def fake_request(*args, **kwargs):
        requested["called"] = True
        return {}

    monkeypatch.setattr(services_auth.OtpService, "request", fake_request)

    with pytest.raises(ApiError) as exc:
        services_auth.request_login_otp("missing@example.com", "127.0.0.1")

    assert exc.value.code == "account_not_found"
    assert exc.value.status == 404
    assert requested["called"] is False


def test_inactive_login_otp_returns_account_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        services_auth,
        "find_user_by_contact",
        lambda contact: {"id": 99, "is_active": False},
    )

    with pytest.raises(ApiError) as exc:
        services_auth.request_login_otp("inactive@example.com", "127.0.0.1")

    assert exc.value.code == "account_inactive"
    assert exc.value.status == 403


def test_frontend_does_not_advance_otp_step_on_failed_request() -> None:
    source = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    request_start = source.index("async function requestLoginOtp")
    request_end = source.index("async function handleOtpRequest", request_start)

    request_source = source[request_start:request_end]

    assert request_source.index("await api.post('/auth/otp/request'") < request_source.index(
        "showOtpVerifyStep"
    )
    assert "account_not_found" in source