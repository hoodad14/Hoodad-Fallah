#!/usr/bin/env python3
"""Send one harmless email through the currently configured SMTP provider."""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
import django

django.setup()

from notifications import NotificationDeliveryError, deliver_test_email, email_transport_status
from exceptions import ApiError
from validators import email as validate_email


def main() -> None:
    parser = argparse.ArgumentParser(description="Test ArenaPass real email delivery.")
    parser.add_argument("--to", required=True, help="Recipient email address")
    args = parser.parse_args()
    try:
        destination = validate_email(args.to)
    except ApiError as exc:
        raise SystemExit(f"Invalid recipient email address: {exc.message}") from exc
    if not destination:
        raise SystemExit("Invalid recipient email address.")

    ready, status = email_transport_status(force=True)
    if not ready:
        raise SystemExit(f"SMTP is not ready: {status}")
    try:
        result = deliver_test_email(destination)
    except NotificationDeliveryError as exc:
        raise SystemExit(f"Email send failed: {exc.diagnostic}") from exc
    print(f"Test email accepted by {result.get('provider', 'provider')} for {destination}.")
    print("Check Inbox and Spam. The message contains no OTP.")


if __name__ == "__main__":
    main()
