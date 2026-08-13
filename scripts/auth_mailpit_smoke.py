#!/usr/bin/env python3
"""End-to-end signup and OTP verification against a running Docker stack.

The script creates a unique spectator, reads its OTP from Mailpit, verifies the
account, checks password login, then checks OTP login. It is intentionally
non-destructive beyond creating one uniquely named test account.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
MAILPIT_BASE = os.getenv("MAILPIT_BASE_URL", "http://127.0.0.1:8080/mailpit").rstrip("/")
OTP_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc
    if not parsed.get("success"):
        raise RuntimeError(f"API failure {url}: {parsed}")
    return parsed["data"]


def wait_url(url: str, timeout: float = 60) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def message_otp(message_id: str, *, email: str, timeout: float = 30) -> str:
    if not message_id:
        query = urllib.parse.quote(f"to:{email}", safe="")
        url = f"{MAILPIT_BASE}/view/latest.txt?query={query}"
    else:
        url = f"{MAILPIT_BASE}/view/{urllib.parse.quote(message_id, safe='')}.txt"
    deadline = time.time() + timeout
    last_body = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                last_body = response.read().decode("utf-8", "replace")
            matches = OTP_RE.findall(last_body)
            if matches:
                return matches[-1]
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        time.sleep(0.5)
    raise RuntimeError(
        f"No OTP found in Mailpit for {email}; message_id={message_id!r}. "
        f"Last body: {last_body[:300]!r}"
    )


def main() -> int:
    wait_url(f"{MAILPIT_BASE}/api/v1/info")
    ready = request_json("GET", f"{API_BASE}/ready")
    if not ready.get("email_transport"):
        raise RuntimeError(f"Backend email transport is not ready: {ready}")
    capabilities = request_json("GET", f"{API_BASE}/auth/capabilities")
    if not capabilities.get("otp", {}).get("email"):
        raise RuntimeError(f"Email OTP capability is unavailable: {capabilities}")

    token = uuid.uuid4().hex[:12]
    email = f"auth-smoke-{token}@example.test"
    password = "StrongPass123"

    signup_request = request_json(
        "POST",
        f"{API_BASE}/auth/signup",
        {
            "first_name": "Auth",
            "last_name": "Smoke",
            "email": email,
            "password": password,
            "preferred_login": "email",
        },
    )
    registration_id = signup_request.get("registration_id")
    if not registration_id:
        raise RuntimeError(f"Signup response has no registration_id: {signup_request}")

    signup_code = message_otp(
        str(signup_request.get("delivery_message_id") or ""), email=email
    )
    signup = request_json(
        "POST",
        f"{API_BASE}/auth/signup/verify",
        {"registration_id": registration_id, "code": signup_code},
    )
    if signup.get("user", {}).get("email") != email:
        raise RuntimeError(f"Verified signup returned unexpected user: {signup}")

    password_login = request_json(
        "POST",
        f"{API_BASE}/auth/password/login",
        {"contact": email, "password": password},
    )
    if not password_login.get("tokens", {}).get("access_token"):
        raise RuntimeError("Password login did not return an access token.")

    login_request = request_json(
        "POST", f"{API_BASE}/auth/otp/request", {"contact": email}
    )
    login_code = message_otp(
        str(login_request.get("delivery_message_id") or ""), email=email
    )
    otp_login = request_json(
        "POST",
        f"{API_BASE}/auth/otp/verify",
        {"contact": email, "code": login_code},
    )
    if not otp_login.get("tokens", {}).get("access_token"):
        raise RuntimeError("OTP login did not return an access token.")

    print("AUTH_MAILPIT_SMOKE=PASS")
    print(f"verified_email={email}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AUTH_MAILPIT_SMOKE=FAIL: {exc}", file=sys.stderr)
        raise
