#!/bin/sh
set -eu

python - <<'PY'
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
import django
django.setup()

import cache
import database
import search_engine
import notifications
from config import config

last_error = ""
for attempt in range(60):
    db_ok = database.ping()
    redis_ok = cache.ping() if config.redis_required else True
    elasticsearch_ok = (
        search_engine.ping() if config.elasticsearch_enabled else True
    )
    email_ok, email_status = (
        notifications.email_transport_status(force=True)
        if config.otp_email_enabled
        else (False, "OTP email delivery is disabled.")
    )
    email_dependency_ok = email_ok or not config.otp_email_required
    if db_ok and redis_ok and elasticsearch_ok and email_dependency_ok:
        try:
            schema = database.fetch_one(
                """
                SELECT
                  to_regclass('public.users') IS NOT NULL AS has_users,
                  to_regclass('public.api_audit_log') IS NOT NULL AS has_audit,
                  to_regclass('public.search_sync_outbox') IS NOT NULL AS has_search_outbox,
                  to_regclass('public.support_conversations') IS NOT NULL AS has_support_conversations,
                  to_regclass('public.support_messages') IS NOT NULL AS has_support_messages,
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
            if schema and all(schema.values()):
                print(
                    "PostgreSQL schema, Redis, OTP email transport and optional search service are ready."
                    if config.otp_email_required
                    else "PostgreSQL schema, Redis and optional search service are ready."
                )
                break
            last_error = f"Database schema is incomplete: {schema}"
        except Exception as exc:
            last_error = str(exc)
    else:
        last_error = (
            f"database={db_ok} redis={redis_ok} elasticsearch={elasticsearch_ok} "
            f"email={email_ok} email_status={email_status}"
        )
    print(f"Waiting for dependencies (attempt {attempt + 1}/60): {last_error}")
    time.sleep(2)
else:
    raise SystemExit(
        "Dependencies or schema did not become ready. "
        "For a changed SQL schema, run 'docker compose down -v' once. "
        f"Last status: {last_error}"
    )
PY

case "${ELASTICSEARCH_ENABLED:-false}" in
  1|true|TRUE|yes|YES|on|ON)
    case "${ELASTICSEARCH_SYNC_ON_STARTUP:-true}" in
      1|true|TRUE|yes|YES|on|ON)
        if [ "${1:-}" = "gunicorn" ]; then
          echo "Synchronizing Elasticsearch ticket index before API startup..."
          python scripts/sync_search_index.py --full
        fi
        ;;
    esac
    ;;
esac

exec "$@"
