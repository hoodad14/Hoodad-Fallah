#!/usr/bin/env python3
"""End-to-end API workflow for a running local ArenaPass stack.

This test intentionally writes data (a uniquely named spectator, reservation,
payment, cancellation/refund and report). Run it only against an isolated local
or CI database. Reset the Docker volume afterwards when a pristine seed is
required.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Result:
    status: int
    payload: dict[str, Any]


class ApiClient:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def call(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        token: str | None = None,
        expected: set[int] | None = None,
    ) -> Result:
        headers = {"Accept": "application/json", "X-Request-ID": f"integration-{secrets.token_hex(6)}"}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.base + path, data=body, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read().decode("utf-8")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                raise AssertionError(f"Non-JSON HTTP {status}: {raw}") from exc
        accepted = expected or {200, 201, 202}
        if status not in accepted:
            raise AssertionError(
                f"{method} {path}: expected {sorted(accepted)}, got {status}: {payload}"
            )
        if status < 400 and payload.get("success") is not True:
            raise AssertionError(f"Unexpected success envelope: {payload}")
        if status >= 400 and payload.get("success") is not False:
            raise AssertionError(f"Unexpected error envelope: {payload}")
        return Result(status, payload)


def data(result: Result) -> Any:
    return result.payload["data"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--yes-destructive",
        action="store_true",
        help="Acknowledge that this creates and mutates records in the target database.",
    )
    args = parser.parse_args()
    if not args.yes_destructive:
        parser.error("Pass --yes-destructive and use only an isolated local/CI database.")

    api = ApiClient(args.base)
    suffix = secrets.token_hex(6)
    email = f"integration.{suffix}@example.com"
    initial_password = "Integration1A"
    changed_password = "Integration2B"

    print("1/17 health and dependency readiness")
    api.call("GET", "/api/v1/health")
    api.call("GET", "/api/v1/ready")

    print("2/17 reject unknown signup fields")
    api.call(
        "POST",
        "/api/v1/auth/signup",
        {
            "first_name": "Contract",
            "last_name": "Probe",
            "email": f"probe.{suffix}@example.com",
            "password": initial_password,
            "role": "support",
        },
        expected={422},
    )

    print("3/17 begin verified spectator registration")
    signup_request = data(
        api.call(
            "POST",
            "/api/v1/auth/signup",
            {
                "first_name": "Integration",
                "last_name": "Tester",
                "email": email,
                "password": initial_password,
                "preferred_login": "email",
                "city_id": 1,
            },
            expected={202},
        )
    )
    signup_code = signup_request.get("debug_code")
    if not signup_code:
        raise AssertionError(
            "The integration test needs OTP_DEBUG_RETURN_CODE=true on an isolated local stack."
        )
    signup = data(
        api.call(
            "POST",
            "/api/v1/auth/signup/verify",
            {
                "registration_id": signup_request["registration_id"],
                "code": signup_code,
            },
            expected={201},
        )
    )
    access = signup["tokens"]["access_token"]
    refresh = signup["tokens"]["refresh_token"]
    user_id = signup["user"]["id"]

    print("4/17 OTP request and one-time verification")
    otp_request = data(
        api.call("POST", "/api/v1/auth/otp/request", {"contact": email}, expected={202})
    )
    code = otp_request.get("debug_code")
    if not code:
        raise AssertionError(
            "The integration test needs OTP_DEBUG_RETURN_CODE=true on an isolated local stack."
        )
    otp_login = data(
        api.call("POST", "/api/v1/auth/otp/verify", {"contact": email, "code": code})
    )
    access = otp_login["tokens"]["access_token"]
    api.call(
        "POST",
        "/api/v1/auth/otp/verify",
        {"contact": email, "code": code},
        expected={400},
    )

    print("5/17 rotate refresh token and reject replay")
    rotated = data(
        api.call("POST", "/api/v1/auth/token/refresh", {"refresh_token": refresh})
    )
    access = rotated["tokens"]["access_token"]
    api.call(
        "POST",
        "/api/v1/auth/token/refresh",
        {"refresh_token": refresh},
        expected={401},
    )

    print("6/17 profile update and password-session invalidation")
    old_access = access
    api.call("PATCH", "/api/v1/profile", {"last_name": "TesterUpdated"}, access)
    password_otp = data(
        api.call(
            "POST",
            "/api/v1/profile/password/otp/request",
            {},
            access,
            expected={202},
        )
    )
    password_code = password_otp.get("debug_code")
    if not password_code:
        raise AssertionError("Password-change OTP debug code was not returned locally.")
    changed = data(
        api.call(
            "POST",
            "/api/v1/profile/password",
            {
                "current_password": initial_password,
                "new_password": changed_password,
                "code": password_code,
            },
            access,
        )
    )
    access = changed["tokens"]["access_token"]
    api.call("GET", "/api/v1/profile", token=old_access, expected={401})
    profile = data(api.call("GET", "/api/v1/profile", token=access))
    assert profile["id"] == user_id and profile["last_name"] == "TesterUpdated"

    print("7/17 lookup APIs")
    for path in (
        "/api/v1/cities",
        "/api/v1/venues",
        "/api/v1/sports",
        "/api/v1/matches",
        "/api/v1/ticket-categories",
        "/api/v1/amenities",
        "/api/v1/payment-methods",
        "/api/v1/report-categories",
    ):
        api.call("GET", path)

    print("8/17 ticket search and detail")
    search = data(api.call("GET", "/api/v1/tickets?page=1&page_size=100"))
    candidates = [item for item in search if int(item["available_quantity"]) >= 1]
    if not candidates:
        raise AssertionError("No future ticket with inventory is available in the seeded database.")
    ticket = candidates[0]
    ticket_id = int(ticket["ticket_id"])
    api.call("GET", f"/api/v1/tickets/{ticket_id}")

    print("9/17 atomic hold and reservation ownership")
    reservation = data(
        api.call(
            "POST",
            "/api/v1/reservations",
            {"ticket_id": ticket_id, "quantity": 1},
            access,
            expected={201},
        )
    )
    reservation_id = int(reservation["reservation_id"])
    api.call("GET", f"/api/v1/reservations/{reservation_id}", token=access)

    print("10/17 local mock payment and issued ticket")
    payment = data(
        api.call(
            "POST",
            f"/api/v1/reservations/{reservation_id}/pay",
            {"payment_method": "local_gateway"},
            access,
        )
    )
    assert payment["payment_status"] == "successful"
    issued = data(api.call("GET", "/api/v1/issued-tickets", token=access))
    assert any(int(item["reservation_id"]) == reservation_id for item in issued)

    print("11/17 support review and optional safe seat correction")
    support_login = data(
        api.call(
            "POST",
            "/api/v1/auth/password/login",
            {"contact": "sara.ahmadi@support.ir", "password": "Demo@123"},
        )
    )
    support_access = support_login["tokens"]["access_token"]
    api.call("GET", "/api/v1/support/dashboard", token=support_access)
    api.call(
        "POST",
        f"/api/v1/support/reservations/{reservation_id}/review",
        {"review_status": "verified", "note": "Verified by integration test"},
        support_access,
    )
    options = data(
        api.call(
            "GET",
            f"/api/v1/seat-change-options?reservation_id={reservation_id}",
            token=access,
        )
    )
    if options:
        correction = data(
            api.call(
                "POST",
                f"/api/v1/support/reservations/{reservation_id}/seat-correction",
                {
                    "new_ticket_id": int(options[0]["ticket_id"]),
                    "note": "Optional safe seat correction in integration test",
                },
                support_access,
            )
        )
        assert int(correction["seat_change_request_id"]) > 0
    else:
        print("  No same-price seat-change candidate in seed; correction branch skipped.")

    print("12/17 cancellation quote and request")
    api.call(
        "GET",
        f"/api/v1/reservations/{reservation_id}/cancellation-quote",
        token=access,
    )
    cancellation = data(
        api.call(
            "POST",
            f"/api/v1/reservations/{reservation_id}/cancellation-requests",
            {"reason": "Automated isolated integration test"},
            access,
            expected={201},
        )
    )
    cancellation_id = int(cancellation["request_id"])

    print("13/17 support refund approval")
    review = data(
        api.call(
            "POST",
            f"/api/v1/support/cancellation-requests/{cancellation_id}/review",
            {"approve": True, "note": "Approved by integration test"},
            support_access,
        )
    )
    assert review["reservation_status"] in {"refunded", "canceled"}

    print("14/17 wallet/refund ledger and booking history")
    api.call("GET", "/api/v1/wallet", token=access)
    bookings = data(api.call("GET", "/api/v1/bookings?scope=canceled", token=access))
    assert any(int(item["reservation_id"]) == reservation_id for item in bookings)

    print("15/17 report submission and support resolution")
    categories = data(api.call("GET", "/api/v1/report-categories"))
    category_id = int(categories[0]["id"])
    report = data(
        api.call(
            "POST",
            "/api/v1/reports",
            {
                "reservation_id": reservation_id,
                "category_id": category_id,
                "subject": "Integration workflow report",
                "description": "Generated by the isolated end-to-end integration test.",
            },
            access,
            expected={201},
        )
    )
    report_id = int(report["id"])
    api.call(
        "PATCH",
        f"/api/v1/support/reports/{report_id}",
        {"status": "resolved", "response": "Resolved by integration test"},
        support_access,
    )

    print("16/17 support filters and access-control boundary")
    api.call("GET", f"/api/v1/support/reservations?user_id={user_id}", token=support_access)
    api.call("GET", "/api/v1/support/dashboard", token=access, expected={403})

    print("17/17 logout and access-token revocation")
    latest_refresh = changed["tokens"]["refresh_token"]
    api.call(
        "POST",
        "/api/v1/auth/logout",
        {"refresh_token": latest_refresh},
        access,
    )
    api.call("GET", "/api/v1/profile", token=access, expected={401})

    print("End-to-end integration workflow passed.")
    print(f"Created isolated test user: {email}")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, TypeError) as exc:
        print(f"INTEGRATION TEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
