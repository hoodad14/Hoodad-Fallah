#!/usr/bin/env python3
"""Fail-fast local verification for files, configuration and live services."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = {
    "00_schema.sql",
    "01_seed_data.sql",
    "02_required_queries.sql",
    "03_required_functions.sql",
    "04_business_functions.sql",
    "05_validation_tests.sql",
    "06_backend_extensions.sql",
    "manage.py",
    "settings.py",
    "urls.py",
    "views.py",
    "worker.py",
    "search_engine.py",
    "services_chat.py",
    "sync_search_index.py",
    "requirements.txt",
    "requirements-dev.txt",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "README.md",
    "AUTHENTICATION_GUIDE.md",
    "auth_mailpit_smoke.py",
    "configure_gmail.py",
    "smtp_smoke.py",
    "پروژه پایانی درس(14).pdf",
}


def verify_files() -> None:
    missing = sorted(name for name in REQUIRED_FILES if not (ROOT / name).is_file())
    if missing:
        raise SystemExit("Missing required files: " + ", ".join(missing))
    for name in ("openapi.json", "ArenaPass.postman_collection.json"):
        with (ROOT / name).open(encoding="utf-8") as handle:
            json.load(handle)


def verify_services() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    import django

    django.setup()
    import cache
    import database
    import search_engine
    from config import config

    if not database.ping():
        raise SystemExit("PostgreSQL is not reachable. Check DATABASE_URL.")
    if config.redis_required and not cache.ping():
        raise SystemExit("Redis is not reachable. Check REDIS_URL.")
    if config.elasticsearch_enabled and not search_engine.ping():
        raise SystemExit(
            "Elasticsearch is enabled but not reachable. Check ELASTICSEARCH_URL."
        )
    if config.elasticsearch_enabled and not search_engine.index_ready():
        raise SystemExit(
            "Elasticsearch is reachable but the ticket index alias is missing. "
            "Run: python sync_search_index.py --full"
        )
    row = database.fetch_one(
        """
        SELECT
          to_regclass('public.users') IS NOT NULL AS has_users,
          to_regclass('public.api_audit_log') IS NOT NULL AS has_audit,
          to_regclass('public.search_sync_outbox') IS NOT NULL AS has_search_outbox,
          EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='users'
              AND column_name='session_version'
          ) AS has_session_version,
          EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='users'
              AND column_name='email_verified_at'
          ) AS has_email_verification,
          EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='users'
              AND column_name='phone_verified_at'
          ) AS has_phone_verification,
          EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='users'
              AND column_name='last_login_at'
          ) AS has_last_login,
          EXISTS(
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='reservations'
              AND column_name='support_review_status'
          ) AS has_support_review,
          to_regprocedure('reserve_ticket(bigint,bigint,integer)') IS NOT NULL AS has_reserve,
          to_regprocedure('process_payment(bigint,bigint,text)') IS NOT NULL AS has_payment
        """
    )
    if not row or not all(row.values()):
        raise SystemExit(
            "Database schema is incomplete. Run all SQL files in documented order. "
            f"Detected: {row}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-services",
        action="store_true",
        help="Only verify package files and JSON documents.",
    )
    args = parser.parse_args()
    verify_files()
    if not args.skip_services:
        verify_services()
    print("ArenaPass preflight passed.")


if __name__ == "__main__":
    main()
