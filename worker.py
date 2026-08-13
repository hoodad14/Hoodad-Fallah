#!/usr/bin/env python3
"""Reservation expiry and optional payment-reminder worker.

Multiple workers are safe: PostgreSQL functions use ``FOR UPDATE SKIP LOCKED``
and Redis ``SET NX`` prevents duplicate reminder delivery.
"""
from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
import django  

django.setup()

import cache  
import database  
import search_engine  
from config import config  
from notifications import (  
    NotificationDeliveryError,
    deliver_payment_reminder,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("arenapass.worker")
running = True


def stop(signum: int, frame: object) -> None:
    del frame
    global running
    running = False
    logger.info("Shutdown signal received: %s", signum)


def _delivery_target(row: dict[str, object]) -> tuple[str, str] | None:
    email = str(row.get("email") or "")
    phone = str(row.get("phone") or "")
    preferred = str(row.get("preferred_login") or "email")
    candidates = (
        (("email", email), ("phone", phone))
        if preferred == "email"
        else (("phone", phone), ("email", email))
    )
    for channel, destination in candidates:
        if channel == "email" and destination and config.otp_email_enabled:
            return channel, destination
        if channel == "phone" and destination and config.otp_sms_webhook_url:
            return channel, destination
    return None


def send_due_payment_reminders() -> int:
    if not config.payment_reminder_enabled:
        return 0
    rows = database.fetch_all(
        """
        SELECT r.id AS reservation_id,r.expires_at,
               u.email::text AS email,u.phone,u.preferred_login
        FROM reservations r
        JOIN users u ON u.id=r.user_id
        WHERE r.status='held'
          AND u.is_active
          AND r.expires_at>CURRENT_TIMESTAMP
          AND r.expires_at<=CURRENT_TIMESTAMP+(%s * INTERVAL '1 second')
        ORDER BY r.expires_at,r.id
        LIMIT 200
        """,
        (config.payment_reminder_before_seconds,),
    )
    sent = 0
    now = datetime.now(timezone.utc)
    for row in rows:
        target = _delivery_target(row)
        if not target:
            continue
        reservation_id = int(row["reservation_id"])
        expires_at = row["expires_at"]
        seconds = max(1, int((expires_at - now).total_seconds()))
        marker = f"payment-reminder:{reservation_id}"
        marker_ttl = seconds + 300
        if not cache.set_once(marker, "sending", marker_ttl):
            continue
        channel, destination = target
        try:
            deliver_payment_reminder(
                channel=channel,
                destination=destination,
                reservation_id=reservation_id,
                expires_in_seconds=seconds,
            )
            cache.client().setex(marker, marker_ttl, "sent")
            sent += 1
        except NotificationDeliveryError:
            cache.delete(marker)
            logger.exception("Payment reminder failed reservation_id=%s", reservation_id)
    return sent


def run_once() -> tuple[int, int, int, int]:
    with database.transaction(isolation="READ COMMITTED") as conn, conn.cursor() as cur:
        cur.execute("SELECT expire_pending_reservations() AS count")
        reservations = int(cur.fetchone()["count"])
        cur.execute("SELECT expire_pending_seat_change_requests() AS count")
        seat_changes = int(cur.fetchone()["count"])
    if reservations or seat_changes:
        cache.bump_version("tickets")
    reminders = send_due_payment_reminders()
    search_updates = (
        search_engine.process_outbox() if config.elasticsearch_enabled else 0
    )
    if search_updates:
        cache.bump_version("tickets")
    return reservations, seat_changes, reminders, search_updates


def main() -> None:
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    interval = config.worker_interval_seconds
    logger.info(
        "Worker started interval=%ss reminders=%s elasticsearch=%s",
        interval,
        config.payment_reminder_enabled,
        config.elasticsearch_enabled,
    )
    last_full_search_sync = 0.0
    if config.elasticsearch_enabled:
        try:
            if not search_engine.alias_exists():
                indexed = search_engine.full_sync(only_if_missing=True)
                logger.info("Initial Elasticsearch reconciliation indexed=%s", indexed)
            last_full_search_sync = time.monotonic()
        except Exception:
            logger.exception("Initial Elasticsearch reconciliation failed")
    while running:
        try:
            reservations, seat_changes, reminders, search_updates = run_once()
            full_search_count = 0
            if (
                config.elasticsearch_enabled
                and time.monotonic() - last_full_search_sync
                >= config.elasticsearch_full_sync_seconds
            ):
                full_search_count = search_engine.full_sync()
                search_updates += search_engine.process_outbox()
                removed_outbox_rows = search_engine.cleanup_outbox()
                if removed_outbox_rows:
                    logger.info(
                        "Cleaned processed search outbox rows=%s",
                        removed_outbox_rows,
                    )
                cache.bump_version("tickets")
                last_full_search_sync = time.monotonic()
            if (
                reservations
                or seat_changes
                or reminders
                or search_updates
                or full_search_count
            ):
                logger.info(
                    "Expired reservations=%s seat_changes=%s reminders=%s "
                    "search_updates=%s full_search_documents=%s",
                    reservations,
                    seat_changes,
                    reminders,
                    search_updates,
                    full_search_count,
                )
        except Exception:
            logger.exception("Worker iteration failed")
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)
    database.close_pool()
    logger.info("Worker stopped")


if __name__ == "__main__":
    main()