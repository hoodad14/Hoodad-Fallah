#!/usr/bin/env python3
"""Configure ArenaPass OTP email delivery without exposing credentials in code."""
from __future__ import annotations

import argparse
import getpass
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"
GMAIL_RE = re.compile(r"^[^\s@]+@(?:gmail\.com|googlemail\.com)$", re.IGNORECASE)


def _load_lines() -> list[str]:
    source = ENV_PATH if ENV_PATH.is_file() else EXAMPLE_PATH
    if not source.is_file():
        raise SystemExit("Neither .env nor .env.example exists.")
    return source.read_text(encoding="utf-8").splitlines()


def _replace(lines: list[str], updates: dict[str, str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in updates:
                result.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        result.append(line)
    missing = [key for key in updates if key not in seen]
    if missing:
        result.extend(["", "# Added by configure_gmail.py"])
        result.extend(f"{key}={updates[key]}" for key in missing)
    return result


def _write(updates: dict[str, str]) -> None:
    content = "\n".join(_replace(_load_lines(), updates)).rstrip() + "\n"
    temp = ENV_PATH.with_suffix(".env.tmp")
    temp.write_text(content, encoding="utf-8")
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(ENV_PATH)
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass


def configure_gmail(email: str | None, app_password: str | None) -> None:
    email = (email or input("Gmail address: ")).strip().lower()
    if not GMAIL_RE.fullmatch(email):
        raise SystemExit("Enter a valid @gmail.com or @googlemail.com address.")

    password = app_password or getpass.getpass("Google App Password: ")
    password = "".join(password.split())
    if len(password) < 12:
        raise SystemExit("The app password looks too short. Do not use the normal Gmail password.")

    _write(
        {
            "OTP_DEBUG_RETURN_CODE": "false",
            "OTP_EMAIL_ENABLED": "true",
            "OTP_EMAIL_REQUIRED": "true",
            "EMAIL_DELIVERY_MODE": "smtp",
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "DEFAULT_FROM_EMAIL": f'"MahTicket <{email}>"',
            "EMAIL_HOST": "smtp.gmail.com",
            "EMAIL_PORT": "587",
            "EMAIL_HOST_USER": email,
            "EMAIL_HOST_PASSWORD": password,
            "EMAIL_USE_TLS": "true",
            "EMAIL_USE_SSL": "false",
            "PUBLIC_MAILPIT_URL": "",
        }
    )
    print("Gmail SMTP was written to .env. The password was not printed.")
    print("Next: docker compose up --build -d")
    print(f"Then test: docker compose exec backend python smtp_smoke.py --to {email}")


def configure_mailpit() -> None:
    _write(
        {
            "OTP_DEBUG_RETURN_CODE": "false",
            "OTP_EMAIL_ENABLED": "true",
            "OTP_EMAIL_REQUIRED": "true",
            "EMAIL_DELIVERY_MODE": "mailpit_api",
            "DEFAULT_FROM_EMAIL": '"MahTicket <noreply@arenapass.local>"',
            "EMAIL_HOST": "mailpit",
            "EMAIL_PORT": "1025",
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": "false",
            "EMAIL_USE_SSL": "false",
            "PUBLIC_MAILPIT_URL": "/mailpit/",
        }
    )
    print("Local Mailpit mode was written to .env.")
    print("Next: docker compose up --build -d")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure real Gmail SMTP delivery or restore local Mailpit."
    )
    parser.add_argument("--email", help="Gmail sender address")
    parser.add_argument(
        "--app-password",
        help="Google App Password. Omit this argument to enter it privately.",
    )
    parser.add_argument(
        "--mailpit", action="store_true", help="Switch back to local Mailpit delivery"
    )
    args = parser.parse_args()
    if args.mailpit:
        configure_mailpit()
        return
    configure_gmail(args.email, args.app_password)


if __name__ == "__main__":
    main()
