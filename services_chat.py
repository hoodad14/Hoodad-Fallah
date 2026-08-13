"""Authenticated spectator/support chat services using direct SQL only."""
from __future__ import annotations

from typing import Any

import database
from audit import record as audit
from exceptions import ApiError, NotFound


MAX_CHAT_MESSAGES = 100


def _conversation_row(cur: Any, conversation_id: int) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT sc.id,sc.spectator_id,sc.assigned_to,sc.status,sc.subject,
               sc.last_message_at,sc.spectator_last_read_at,sc.support_last_read_at,
               sc.created_at,sc.updated_at,
               spectator.first_name AS spectator_first_name,
               spectator.last_name AS spectator_last_name,
               spectator.email::text AS spectator_email,
               spectator.phone AS spectator_phone,
               support.first_name AS support_first_name,
               support.last_name AS support_last_name
        FROM support_conversations sc
        JOIN users spectator ON spectator.id=sc.spectator_id
        LEFT JOIN users support ON support.id=sc.assigned_to
        WHERE sc.id=%s
        """,
        (conversation_id,),
    )
    return cur.fetchone()


def _messages(cur: Any, conversation_id: int, *, after_id: int = 0, limit: int = MAX_CHAT_MESSAGES) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT sm.id,sm.conversation_id,sm.sender_id,sm.body,sm.created_at,sm.read_at,
               u.role AS sender_role,u.first_name,u.last_name
        FROM support_messages sm
        JOIN users u ON u.id=sm.sender_id
        WHERE sm.conversation_id=%s AND sm.id>%s
        ORDER BY sm.id ASC
        LIMIT %s
        """,
        (conversation_id, after_id, limit),
    )
    return list(cur.fetchall())


def get_spectator_chat(
    spectator_id: int,
    *,
    after_id: int = 0,
    limit: int = MAX_CHAT_MESSAGES,
    mark_read: bool = False,
) -> dict[str, Any]:
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM support_conversations WHERE spectator_id=%s",
            (spectator_id,),
        )
        found = cur.fetchone()
        if not found:
            return {"conversation": None, "messages": [], "unread_count": 0}
        conversation_id = int(found["id"])
        if mark_read:
            cur.execute(
                """
                UPDATE support_conversations
                SET spectator_last_read_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (conversation_id,),
            )
            cur.execute(
                """
                UPDATE support_messages sm
                SET read_at=COALESCE(sm.read_at,CURRENT_TIMESTAMP)
                FROM users sender
                WHERE sm.sender_id=sender.id
                  AND sm.conversation_id=%s
                  AND sender.role='support'
                  AND sm.read_at IS NULL
                """,
                (conversation_id,),
            )
        conversation = _conversation_row(cur, conversation_id)
        messages = _messages(cur, conversation_id, after_id=after_id, limit=limit)
        cur.execute(
            """
            SELECT COUNT(*) AS unread_count
            FROM support_messages sm
            JOIN users sender ON sender.id=sm.sender_id
            JOIN support_conversations sc ON sc.id=sm.conversation_id
            WHERE sm.conversation_id=%s
              AND sender.role='support'
              AND (sc.spectator_last_read_at IS NULL OR sm.created_at>sc.spectator_last_read_at)
            """,
            (conversation_id,),
        )
        unread_count = int(cur.fetchone()["unread_count"])
        return {
            "conversation": conversation,
            "messages": messages,
            "unread_count": unread_count,
        }


def send_spectator_message(
    spectator_id: int,
    body: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    cleaned = body.strip()
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM users WHERE id=%s AND role='spectator' AND is_active FOR SHARE",
            (spectator_id,),
        )
        if not cur.fetchone():
            raise ApiError("account_unavailable", "Spectator account is not active.", 403)
        cur.execute(
            """
            INSERT INTO support_conversations (spectator_id,status,subject,last_message_at)
            VALUES (%s,'open','گفتگو با پشتیبانی MahTicket',CURRENT_TIMESTAMP)
            ON CONFLICT (spectator_id) DO UPDATE
            SET status='open',updated_at=CURRENT_TIMESTAMP
            RETURNING id
            """,
            (spectator_id,),
        )
        conversation_id = int(cur.fetchone()["id"])
        cur.execute(
            """
            INSERT INTO support_messages (conversation_id,sender_id,body)
            VALUES (%s,%s,%s)
            RETURNING id,conversation_id,sender_id,body,created_at,read_at
            """,
            (conversation_id, spectator_id, cleaned),
        )
        message = cur.fetchone()
        cur.execute(
            """
            UPDATE support_conversations
            SET last_message_at=%s,updated_at=CURRENT_TIMESTAMP,status='open'
            WHERE id=%s
            """,
            (message["created_at"], conversation_id),
        )
        audit(
            conn,
            actor_user_id=spectator_id,
            action="support_chat.message.create",
            resource_type="support_conversation",
            resource_id=conversation_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"message_id": message["id"], "sender_role": "spectator"},
        )
        message["sender_role"] = "spectator"
        return message


def mark_spectator_read(spectator_id: int) -> dict[str, Any]:
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM support_conversations WHERE spectator_id=%s",
            (spectator_id,),
        )
        found = cur.fetchone()
        if not found:
            return {"conversation_id": None, "marked": 0}
        conversation_id = int(found["id"])
        cur.execute(
            """
            UPDATE support_messages sm
            SET read_at=COALESCE(sm.read_at,CURRENT_TIMESTAMP)
            FROM users sender
            WHERE sm.sender_id=sender.id
              AND sm.conversation_id=%s
              AND sender.role='support'
              AND sm.read_at IS NULL
            """,
            (conversation_id,),
        )
        marked = cur.rowcount
        cur.execute(
            "UPDATE support_conversations SET spectator_last_read_at=CURRENT_TIMESTAMP WHERE id=%s",
            (conversation_id,),
        )
        return {"conversation_id": conversation_id, "marked": marked}


def list_support_conversations(
    *,
    status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    clauses = ["TRUE"]
    params: list[Any] = []
    if status:
        clauses.append("sc.status=%s")
        params.append(status)
    where = " AND ".join(clauses)
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM support_conversations sc WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT sc.id,sc.spectator_id,sc.assigned_to,sc.status,sc.subject,
                   sc.last_message_at,sc.created_at,sc.updated_at,
                   spectator.first_name,spectator.last_name,
                   spectator.email::text AS email,spectator.phone,
                   assignee.first_name AS assignee_first_name,
                   assignee.last_name AS assignee_last_name,
                   latest.body AS latest_message,
                   latest.sender_id AS latest_sender_id,
                   COALESCE(unread.unread_count,0)::BIGINT AS unread_count
            FROM support_conversations sc
            JOIN users spectator ON spectator.id=sc.spectator_id
            LEFT JOIN users assignee ON assignee.id=sc.assigned_to
            LEFT JOIN LATERAL (
                SELECT sm.body,sm.sender_id
                FROM support_messages sm
                WHERE sm.conversation_id=sc.id
                ORDER BY sm.id DESC LIMIT 1
            ) latest ON TRUE
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS unread_count
                FROM support_messages sm
                WHERE sm.conversation_id=sc.id
                  AND sm.sender_id=sc.spectator_id
                  AND (sc.support_last_read_at IS NULL OR sm.created_at>sc.support_last_read_at)
            ) unread ON TRUE
            WHERE {where}
            ORDER BY (COALESCE(unread.unread_count,0)>0) DESC,sc.last_message_at DESC,sc.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def get_support_conversation(
    support_id: int,
    conversation_id: int,
    *,
    after_id: int = 0,
    limit: int = MAX_CHAT_MESSAGES,
    mark_read: bool = True,
) -> dict[str, Any]:
    with database.transaction() as conn, conn.cursor() as cur:
        conversation = _conversation_row(cur, conversation_id)
        if not conversation:
            raise NotFound("Support conversation not found.")
        if mark_read:
            cur.execute(
                "UPDATE support_conversations SET support_last_read_at=CURRENT_TIMESTAMP WHERE id=%s",
                (conversation_id,),
            )
            cur.execute(
                """
                UPDATE support_messages
                SET read_at=COALESCE(read_at,CURRENT_TIMESTAMP)
                WHERE conversation_id=%s AND sender_id=%s AND read_at IS NULL
                """,
                (conversation_id, conversation["spectator_id"]),
            )
        messages = _messages(cur, conversation_id, after_id=after_id, limit=limit)
        conversation = _conversation_row(cur, conversation_id)
        return {"conversation": conversation, "messages": messages}


def send_support_message(
    support_id: int,
    conversation_id: int,
    body: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    cleaned = body.strip()
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM users WHERE id=%s AND role='support' AND is_active FOR SHARE",
            (support_id,),
        )
        if not cur.fetchone():
            raise ApiError("account_unavailable", "Support account is not active.", 403)
        cur.execute(
            "SELECT id,status FROM support_conversations WHERE id=%s FOR UPDATE",
            (conversation_id,),
        )
        conversation = cur.fetchone()
        if not conversation:
            raise NotFound("Support conversation not found.")
        cur.execute(
            """
            INSERT INTO support_messages (conversation_id,sender_id,body)
            VALUES (%s,%s,%s)
            RETURNING id,conversation_id,sender_id,body,created_at,read_at
            """,
            (conversation_id, support_id, cleaned),
        )
        message = cur.fetchone()
        cur.execute(
            """
            UPDATE support_conversations
            SET assigned_to=COALESCE(assigned_to,%s),status='open',
                support_last_read_at=CURRENT_TIMESTAMP,last_message_at=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            (support_id, message["created_at"], conversation_id),
        )
        audit(
            conn,
            actor_user_id=support_id,
            action="support_chat.message.reply",
            resource_type="support_conversation",
            resource_id=conversation_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"message_id": message["id"], "sender_role": "support"},
        )
        message["sender_role"] = "support"
        return message


def set_conversation_status(
    support_id: int,
    conversation_id: int,
    status: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    if status not in {"open", "closed"}:
        raise ApiError("validation_error", "Invalid chat status.", 422)
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE support_conversations
            SET status=%s,assigned_to=COALESCE(assigned_to,%s),updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            RETURNING id,status,assigned_to,updated_at
            """,
            (status, support_id, conversation_id),
        )
        result = cur.fetchone()
        if not result:
            raise NotFound("Support conversation not found.")
        audit(
            conn,
            actor_user_id=support_id,
            action="support_chat.status.update",
            resource_type="support_conversation",
            resource_id=conversation_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"status": status},
        )
        return result
