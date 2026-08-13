"""Best-effort database audit logging for sensitive changes."""
from __future__ import annotations

import json
import logging
from typing import Any

from psycopg import Connection

logger = logging.getLogger(__name__)


def record(
    conn: Connection[Any],
    *,
    actor_user_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | int | None,
    request_id: str | None,
    ip_address: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO api_audit_log
                (actor_user_id,action,resource_type,resource_id,request_id,ip_address,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
            """,
            (
                actor_user_id,
                action,
                resource_type,
                None if resource_id is None else str(resource_id),
                request_id,
                ip_address,
                json.dumps(metadata or {}, ensure_ascii=False, default=str),
            ),
        )
