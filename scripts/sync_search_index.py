#!/usr/bin/env python3
"""Create/reconcile the Elasticsearch ticket index from PostgreSQL."""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, "/app")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django  # noqa: E402

django.setup()

import cache  # noqa: E402
import search_engine  # noqa: E402
from config import config  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="Rebuild a fresh concrete index and atomically switch the alias.",
    )
    parser.add_argument(
        "--outbox-only",
        action="store_true",
        help="Process pending transactional outbox rows only.",
    )
    args = parser.parse_args()
    if not config.elasticsearch_enabled:
        print("Elasticsearch is disabled; no synchronization was performed.")
        return
    if not search_engine.ping():
        raise SystemExit("Elasticsearch is not reachable. Check ELASTICSEARCH_URL.")
    if args.outbox_only:
        count = search_engine.process_outbox()
        if count:
            cache.bump_version("tickets")
        print(f"Processed {count} search outbox row(s).")
        return
    # Full reconciliation is the safe default for a manually invoked command.
    count = search_engine.full_sync()
    pending = search_engine.process_outbox()
    cache.bump_version("tickets")
    print(
        f"Elasticsearch full sync completed: {count} ticket document(s); "
        f"{pending} concurrent outbox row(s) processed."
    )


if __name__ == "__main__":
    main()
