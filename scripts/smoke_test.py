#!/usr/bin/env python3
"""Non-destructive live smoke test for a running backend."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def call(base: str, method: str, path: str, data: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(base + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        raise
    assert payload.get("success") is True, payload
    return payload["data"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print("1/6 health")
    call(base, "GET", "/api/v1/health")
    print("2/6 readiness")
    call(base, "GET", "/api/v1/ready")
    print("3/6 password login with seeded spectator")
    login = call(
        base,
        "POST",
        "/api/v1/auth/password/login",
        {"contact": "hossein.m@gmail.com", "password": "Demo@123"},
    )
    token = login["tokens"]["access_token"]
    print("4/6 profile")
    call(base, "GET", "/api/v1/profile", token=token)
    print("5/6 ticket search")
    call(base, "GET", "/api/v1/tickets?page=1&page_size=5")
    print("6/6 reservation history")
    call(base, "GET", "/api/v1/reservations?page=1&page_size=5", token=token)
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
