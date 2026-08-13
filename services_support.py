"""Support-only operational services."""
from __future__ import annotations

from typing import Any

import cache
import database
from audit import record as audit
from exceptions import ApiError, NotFound
from services_catalog import invalidate_ticket_cache


def _validate_ticket_state(ticket: dict[str, Any]) -> None:
    """Validate cross-field ticket invariants before relying on DB constraints."""
    is_numbered = bool(ticket["is_numbered"])
    row_code = ticket.get("row_code")
    seat_code = ticket.get("seat_code")
    capacity = int(ticket["total_capacity"])
    if is_numbered:
        if not row_code or not seat_code:
            raise ApiError(
                "validation_error",
                "Numbered tickets require both row_code and seat_code.",
                422,
            )
        if capacity != 1:
            raise ApiError(
                "validation_error",
                "A numbered ticket must have total_capacity equal to 1.",
                422,
            )
    elif row_code is not None or seat_code is not None:
        raise ApiError(
            "validation_error",
            "General-admission tickets cannot define row_code or seat_code.",
            422,
        )

    sale_starts_at = ticket.get("sale_starts_at")
    sale_ends_at = ticket.get("sale_ends_at")
    if sale_starts_at is not None and sale_ends_at is not None and sale_ends_at <= sale_starts_at:
        raise ApiError(
            "validation_error",
            "sale_ends_at must be later than sale_starts_at.",
            422,
        )

    allocated = (
        int(ticket.get("held_quantity", 0))
        + int(ticket.get("sold_quantity", 0))
        + int(ticket.get("change_held_quantity", 0))
    )
    if capacity < allocated:
        raise ApiError(
            "business_rule_violation",
            "total_capacity cannot be lower than already allocated inventory.",
            409,
            {"allocated_quantity": allocated},
        )


def dashboard() -> dict[str, Any]:
    return database.fetch_one(
        """
        SELECT
          (SELECT COUNT(*) FROM users WHERE role='spectator' AND is_active) AS active_spectators,
          (SELECT COUNT(*) FROM tickets WHERE is_active) AS active_ticket_rows,
          (SELECT COUNT(*) FROM reservations WHERE status='held') AS held_reservations,
          (SELECT COUNT(*) FROM reservations WHERE status='paid') AS paid_reservations,
          (SELECT COUNT(*) FROM reservations WHERE support_review_status='needs_correction') AS reservations_needing_correction,
          (SELECT COUNT(*) FROM cancellation_requests WHERE status='pending') AS pending_cancellations,
          (SELECT COUNT(*) FROM seat_change_requests WHERE status='pending') AS pending_seat_changes,
          (SELECT COUNT(*) FROM reports WHERE status IN ('pending','in_review')) AS open_reports,
          (SELECT COUNT(*) FROM support_conversations WHERE status='open') AS open_chats,
          (SELECT COUNT(DISTINCT sc.id)
             FROM support_conversations sc
             JOIN support_messages sm ON sm.conversation_id=sc.id
            WHERE sm.sender_id=sc.spectator_id
              AND (sc.support_last_read_at IS NULL OR sm.created_at>sc.support_last_read_at)) AS unread_chats,
          (SELECT COUNT(*) FROM payments WHERE status='failed' AND created_at>=CURRENT_TIMESTAMP-INTERVAL '24 hours') AS failed_payments_24h,
          (SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='successful' AND paid_at>=date_trunc('day',CURRENT_TIMESTAMP)) AS successful_volume_today
        """
    ) or {}


def list_reservations(
    *,
    status: str | None,
    user_id: int | None,
    review_status: str | None,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    clauses = ["TRUE"]
    params: list[Any] = []
    if status:
        clauses.append("r.status=%s")
        params.append(status)
    if user_id:
        clauses.append("r.user_id=%s")
        params.append(user_id)
    if review_status:
        clauses.append("r.support_review_status=%s")
        params.append(review_status)
    where = " AND ".join(clauses)
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM reservations r WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT r.id,r.user_id,u.first_name,u.last_name,u.email::text AS email,u.phone,
                   r.status,r.quantity,r.total_amount,r.reserved_at,r.expires_at,r.paid_at,
                   r.canceled_at,r.cancellation_reason,r.support_review_status,
                   r.support_review_note,r.support_reviewed_at,r.support_reviewed_by,
                   reviewer.first_name AS reviewer_first_name,
                   reviewer.last_name AS reviewer_last_name,
                   vc.ticket_id,vc.sport_name,vc.home_team,vc.away_team,vc.starts_at,
                   vc.venue_name,vc.category_name,vc.section_code,vc.row_code,vc.seat_code
            FROM reservations r
            JOIN users u ON u.id=r.user_id
            LEFT JOIN users reviewer ON reviewer.id=r.support_reviewed_by
            JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
            WHERE {where}
            ORDER BY r.reserved_at DESC,r.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def review_reservation(
    support_id: int,
    reservation_id: int,
    review_status: str,
    note: str | None,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    """Persist support confirmation/problem review without forging payment state."""
    allowed = {"verified", "needs_correction"}
    if review_status not in allowed:
        raise ApiError("validation_error", "Invalid reservation review status.", 422)
    if review_status == "needs_correction" and not note:
        raise ApiError(
            "validation_error",
            "A review note is required when correction is needed.",
            422,
        )
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE reservations
            SET support_review_status=%s,
                support_reviewed_by=%s,
                support_review_note=%s,
                support_reviewed_at=CURRENT_TIMESTAMP
            WHERE id=%s
            RETURNING id,status,support_review_status,support_reviewed_by,
                      support_review_note,support_reviewed_at
            """,
            (review_status, support_id, note, reservation_id),
        )
        result = cur.fetchone()
        if not result:
            raise NotFound("Reservation not found.")
        audit(
            conn,
            actor_user_id=support_id,
            action="support.reservation.review",
            resource_type="reservation",
            resource_id=reservation_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"review_status": review_status, "note": note},
        )
    return result


def correct_reservation_seat(
    support_id: int,
    reservation_id: int,
    new_ticket_id: int,
    note: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    """Apply a same-match/same-price seat correction through safe DB workflows."""
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT user_id,status FROM reservations WHERE id=%s FOR UPDATE",
            (reservation_id,),
        )
        reservation = cur.fetchone()
        if not reservation:
            raise NotFound("Reservation not found.")
        if reservation["status"] not in {"held", "paid"}:
            raise ApiError(
                "business_rule_violation",
                "Only held or paid reservations can receive a seat correction.",
                409,
            )
        cur.execute(
            "SELECT request_seat_change(%s,%s,%s) AS request_id",
            (reservation["user_id"], reservation_id, new_ticket_id),
        )
        seat_request_id = int(cur.fetchone()["request_id"])
        cur.execute(
            "SELECT * FROM review_seat_change(%s,%s,TRUE,%s)",
            (support_id, seat_request_id, note),
        )
        result = cur.fetchone()
        cur.execute(
            """
            UPDATE reservations
            SET support_review_status='verified',
                support_reviewed_by=%s,
                support_review_note=%s,
                support_reviewed_at=CURRENT_TIMESTAMP
            WHERE id=%s
            """,
            (support_id, note, reservation_id),
        )
        audit(
            conn,
            actor_user_id=support_id,
            action="support.reservation.seat_correct",
            resource_type="reservation",
            resource_id=reservation_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={
                "new_ticket_id": new_ticket_id,
                "seat_change_request_id": seat_request_id,
            },
        )
    invalidate_ticket_cache()
    return {"seat_change_request_id": seat_request_id, **result}


def cancel_held_reservation(
    support_id: int,
    reservation_id: int,
    reason: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM support_cancel_reservation(%s,%s,%s)",
            (support_id, reservation_id, reason),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=support_id,
            action="support.reservation.cancel",
            resource_type="reservation",
            resource_id=reservation_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"reason": reason},
        )
    invalidate_ticket_cache()
    return result


def suspicious_payments(page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    predicate = """
      p.status='failed'
      OR (p.status='pending' AND p.created_at<CURRENT_TIMESTAMP-INTERVAL '5 minutes')
      OR (SELECT COUNT(*) FROM payments p2 WHERE p2.reservation_id=p.reservation_id AND p2.status='failed')>=2
    """
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM payments p WHERE {predicate}")
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT p.id,p.reservation_id,p.amount,p.status,p.transaction_ref,p.failure_reason,
                   p.created_at,p.paid_at,pm.code AS method_code,
                   r.user_id,u.first_name,u.last_name,u.email::text AS email,u.phone,
                   (SELECT COUNT(*) FROM payments p2 WHERE p2.reservation_id=p.reservation_id AND p2.status='failed') AS failed_attempts
            FROM payments p
            JOIN payment_methods pm ON pm.id=p.payment_method_id
            JOIN reservations r ON r.id=p.reservation_id
            JOIN users u ON u.id=r.user_id
            WHERE {predicate}
            ORDER BY p.created_at DESC,p.id DESC
            LIMIT %s OFFSET %s
            """,
            (page_size, (page - 1) * page_size),
        )
        return list(cur.fetchall()), total


def list_cancellation_requests(status: str | None, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    where = "TRUE" if not status else "cr.status=%s"
    params: list[Any] = [] if not status else [status]
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM cancellation_requests cr WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT cr.id,cr.reservation_id,cr.reason,cr.status,cr.estimated_penalty_pct,
                   cr.estimated_refund,cr.review_note,cr.requested_at,cr.reviewed_at,
                   u.id AS user_id,u.first_name,u.last_name,u.email::text AS email,u.phone,
                   su.first_name AS reviewer_first_name,su.last_name AS reviewer_last_name,
                   vc.sport_name,vc.home_team,vc.away_team,vc.starts_at,vc.venue_name
            FROM cancellation_requests cr
            JOIN reservations r ON r.id=cr.reservation_id
            JOIN users u ON u.id=r.user_id
            JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
            LEFT JOIN users su ON su.id=cr.reviewed_by
            WHERE {where}
            ORDER BY cr.requested_at ASC,cr.id ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def review_cancellation(
    support_id: int,
    request_id_value: int,
    approve: bool,
    note: str | None,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM review_cancellation(%s,%s,%s,%s)",
            (support_id, request_id_value, approve, note),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=support_id,
            action="support.cancellation.review",
            resource_type="cancellation_request",
            resource_id=request_id_value,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"approve": approve, "result": result},
        )
    invalidate_ticket_cache()
    return result


def list_seat_change_requests(status: str | None, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    where = "TRUE" if not status else "scr.status=%s"
    params: list[Any] = [] if not status else [status]
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM seat_change_requests scr WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT scr.id,scr.reservation_id,scr.status,scr.quantity,scr.old_unit_price,
                   scr.new_unit_price,scr.target_hold_expires_at,scr.requested_at,
                   scr.reviewed_at,scr.review_note,
                   u.id AS user_id,u.first_name,u.last_name,u.email::text AS email,u.phone,
                   oldt.section_code AS old_section,oldt.row_code AS old_row,oldt.seat_code AS old_seat,
                   newt.section_code AS new_section,newt.row_code AS new_row,newt.seat_code AS new_seat,
                   vc.home_team,vc.away_team,vc.starts_at,vc.venue_name
            FROM seat_change_requests scr
            JOIN reservations r ON r.id=scr.reservation_id
            JOIN users u ON u.id=r.user_id
            JOIN tickets oldt ON oldt.id=scr.old_ticket_id
            JOIN tickets newt ON newt.id=scr.requested_ticket_id
            JOIN v_ticket_catalog vc ON vc.ticket_id=oldt.id
            WHERE {where}
            ORDER BY scr.requested_at ASC,scr.id ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def review_seat_change(
    support_id: int,
    request_id_value: int,
    approve: bool,
    note: str | None,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM review_seat_change(%s,%s,%s,%s)",
            (support_id, request_id_value, approve, note),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=support_id,
            action="support.seat_change.review",
            resource_type="seat_change_request",
            resource_id=request_id_value,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"approve": approve, "result": result},
        )
    invalidate_ticket_cache()
    return result


def list_reports(status: str | None, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    where = "TRUE" if not status else "rp.status=%s"
    params: list[Any] = [] if not status else [status]
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM reports rp WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT rp.id,rp.ticket_id,rp.reservation_id,rp.payment_id,rp.subject,
                   rp.description,rp.status,rp.support_response,rp.created_at,rp.updated_at,
                   rp.resolved_at,rc.code AS category_code,rc.name AS category_name,
                   u.id AS reporter_id,u.first_name,u.last_name,u.email::text AS email,u.phone,
                   su.id AS assigned_to,su.first_name AS support_first_name,su.last_name AS support_last_name
            FROM reports rp
            JOIN report_categories rc ON rc.id=rp.category_id
            JOIN users u ON u.id=rp.reporter_id
            LEFT JOIN users su ON su.id=rp.assigned_to
            WHERE {where}
            ORDER BY CASE rp.status WHEN 'pending' THEN 0 WHEN 'in_review' THEN 1 ELSE 2 END,
                     rp.created_at ASC,rp.id ASC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def update_report(
    support_id: int,
    report_id: int,
    *,
    status: str,
    response: str | None,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    allowed = {"pending", "in_review", "resolved", "rejected"}
    if status not in allowed:
        raise ApiError("validation_error", "Invalid report status.", 422)
    if status in {"resolved", "rejected"} and not response:
        raise ApiError("validation_error", "A support response is required to close a report.", 422)
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute("SELECT id,status FROM reports WHERE id=%s FOR UPDATE", (report_id,))
        current = cur.fetchone()
        if not current:
            raise NotFound("Report not found.")
        transitions = {
            "pending": {"pending", "in_review", "resolved", "rejected"},
            "in_review": {"in_review", "resolved", "rejected"},
            "resolved": {"resolved"},
            "rejected": {"rejected"},
        }
        if status not in transitions[current["status"]]:
            raise ApiError(
                "business_rule_violation",
                f"Report status cannot change from {current['status']} to {status}.",
                409,
            )
        assigned_to = None if status == "pending" else support_id
        resolved_at_sql = "CURRENT_TIMESTAMP" if status in {"resolved", "rejected"} else "NULL"
        cur.execute(
            f"""
            UPDATE reports
            SET status=%s,assigned_to=%s,support_response=%s,resolved_at={resolved_at_sql}
            WHERE id=%s
            RETURNING id,status,assigned_to,support_response,resolved_at,updated_at
            """,
            (status, assigned_to, response, report_id),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=support_id,
            action="support.report.update",
            resource_type="report",
            resource_id=report_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"status": status},
        )
    return result


def deactivate_user(
    support_id: int,
    target_user_id: int,
    reason: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute("SELECT deactivate_user(%s,%s,%s) AS released_reservations", (support_id, target_user_id, reason))
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=support_id,
            action="support.user.deactivate",
            resource_type="user",
            resource_id=target_user_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"reason": reason, **result},
        )
    cache.delete(f"profile:{target_user_id}")
    cache.revoke_user_refresh_tokens(target_user_id)
    invalidate_ticket_cache()
    return result


def list_tickets(page: int, page_size: int, include_inactive: bool = True) -> tuple[list[dict[str, Any]], int]:
    where = "TRUE" if include_inactive else "vc.is_active"
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM v_ticket_catalog vc WHERE {where}")
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT vc.*,
                   COALESCE(
                     (SELECT jsonb_agg(ta.amenity_id ORDER BY ta.amenity_id)
                        FROM ticket_amenities ta
                       WHERE ta.ticket_id=vc.ticket_id),
                     '[]'::jsonb
                   ) AS amenity_ids
            FROM v_ticket_catalog vc
            WHERE {where}
            ORDER BY starts_at DESC,ticket_id DESC
            LIMIT %s OFFSET %s
            """,
            (page_size, (page - 1) * page_size),
        )
        return list(cur.fetchall()), total


def create_ticket(support_id: int, data: dict[str, Any], *, request_id: str | None, ip_address: str) -> dict[str, Any]:
    _validate_ticket_state(data)
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tickets
              (match_id,ticket_category_id,section_code,row_code,seat_code,is_numbered,
               price,total_capacity,sale_starts_at,sale_ends_at,is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                data["match_id"], data["ticket_category_id"], data["section_code"],
                data.get("row_code"), data.get("seat_code"), data["is_numbered"],
                data["price"], data["total_capacity"], data.get("sale_starts_at"),
                data.get("sale_ends_at"), data.get("is_active", True),
            ),
        )
        ticket_id = cur.fetchone()["id"]
        for amenity_id in dict.fromkeys(data.get("amenity_ids", [])):
            cur.execute(
                "INSERT INTO ticket_amenities(ticket_id,amenity_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (ticket_id, amenity_id),
            )
        audit(
            conn, actor_user_id=support_id, action="support.ticket.create",
            resource_type="ticket", resource_id=ticket_id, request_id=request_id,
            ip_address=ip_address, metadata={"match_id": data["match_id"]},
        )
    invalidate_ticket_cache()
    from services_catalog import ticket_detail
    return ticket_detail(ticket_id, include_inactive=True)


def update_ticket(support_id: int, ticket_id: int, fields: dict[str, Any], *, request_id: str | None, ip_address: str) -> dict[str, Any]:
    if fields.get("is_active") is False:
        raise ApiError(
            "validation_error",
            "Use the dedicated DELETE endpoint to deactivate a ticket safely.",
            422,
        )
    allowed = {
        "ticket_category_id", "section_code", "row_code", "seat_code", "is_numbered",
        "price", "total_capacity", "sale_starts_at", "sale_ends_at", "is_active",
    }
    updates = [(k, v) for k, v in fields.items() if k in allowed]
    amenity_ids = fields.get("amenity_ids")
    if not updates and amenity_ids is None:
        raise ApiError("validation_error", "No editable ticket field was supplied.", 422)
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,ticket_category_id,section_code,row_code,seat_code,is_numbered,
                   price,total_capacity,held_quantity,sold_quantity,change_held_quantity,
                   sale_starts_at,sale_ends_at,is_active
            FROM tickets
            WHERE id=%s
            FOR UPDATE
            """,
            (ticket_id,),
        )
        current = cur.fetchone()
        if not current:
            raise NotFound("Ticket not found.")
        merged = dict(current)
        merged.update({key: value for key, value in updates})
        _validate_ticket_state(merged)
        if updates:
            assignments = ",".join(f"{column}=%s" for column, _ in updates)
            cur.execute(
                f"UPDATE tickets SET {assignments} WHERE id=%s",
                tuple([value for _, value in updates] + [ticket_id]),
            )
        if amenity_ids is not None:
            cur.execute("DELETE FROM ticket_amenities WHERE ticket_id=%s", (ticket_id,))
            for amenity_id in dict.fromkeys(amenity_ids):
                cur.execute(
                    "INSERT INTO ticket_amenities(ticket_id,amenity_id) VALUES (%s,%s)",
                    (ticket_id, amenity_id),
                )
        audit(
            conn, actor_user_id=support_id, action="support.ticket.update",
            resource_type="ticket", resource_id=ticket_id, request_id=request_id,
            ip_address=ip_address, metadata={"fields": [k for k, _ in updates] + (["amenity_ids"] if amenity_ids is not None else [])},
        )
    invalidate_ticket_cache()
    from services_catalog import ticket_detail
    return ticket_detail(ticket_id, include_inactive=True)


def deactivate_ticket(support_id: int, ticket_id: int, *, request_id: str | None, ip_address: str) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,is_active,held_quantity,change_held_quantity
            FROM tickets
            WHERE id=%s
            FOR UPDATE
            """,
            (ticket_id,),
        )
        ticket = cur.fetchone()
        if not ticket:
            raise NotFound("Ticket not found.")

        cur.execute(
            """
            SELECT
              EXISTS(
                SELECT 1 FROM reservations r
                WHERE r.ticket_id=%s AND r.status='held'
              ) AS has_reservation_holds,
              EXISTS(
                SELECT 1 FROM seat_change_requests scr
                WHERE scr.requested_ticket_id=%s AND scr.status='pending'
              ) AS has_seat_change_holds
            """,
            (ticket_id, ticket_id),
        )
        holds = cur.fetchone()
        if (
            int(ticket["held_quantity"]) > 0
            or int(ticket["change_held_quantity"]) > 0
            or holds["has_reservation_holds"]
            or holds["has_seat_change_holds"]
        ):
            raise ApiError(
                "business_rule_violation",
                "Ticket cannot be deactivated while reservation or seat-change holds are active.",
                409,
            )

        cur.execute(
            "UPDATE tickets SET is_active=FALSE WHERE id=%s RETURNING id,is_active",
            (ticket_id,),
        )
        result = cur.fetchone()
        audit(
            conn, actor_user_id=support_id, action="support.ticket.deactivate",
            resource_type="ticket", resource_id=ticket_id, request_id=request_id,
            ip_address=ip_address,
        )
    invalidate_ticket_cache()
    return result
