"""Reservation, payment, wallet, refund, seat-change, and report use-cases."""
from __future__ import annotations

from typing import Any

import cache
import database
from audit import record as audit
from exceptions import ApiError, NotFound
from services_catalog import invalidate_ticket_cache


def _expire_due(conn: Any) -> tuple[int, int]:
    """Expire due holds and return affected counts inside the caller transaction."""
    with conn.cursor() as cur:
        cur.execute("SELECT expire_pending_reservations() AS reservations")
        reservations = int(cur.fetchone()["reservations"])
        cur.execute("SELECT expire_pending_seat_change_requests() AS seat_changes")
        seat_changes = int(cur.fetchone()["seat_changes"])
    return reservations, seat_changes


def wallet(user_id: int) -> dict[str, Any]:
    row = database.fetch_one(
        """
        SELECT w.id,w.balance,w.currency,w.updated_at,
               COALESCE((
                   SELECT jsonb_agg(jsonb_build_object(
                       'id',wt.id,'type',wt.transaction_type,'amount',wt.amount,
                       'balance_after',wt.balance_after,'reference_code',wt.reference_code,
                       'description',wt.description,'created_at',wt.created_at
                   ) ORDER BY wt.created_at DESC)
                   FROM (SELECT * FROM wallet_transactions WHERE wallet_id=w.id ORDER BY created_at DESC LIMIT 50) wt
               ),'[]'::jsonb) AS recent_transactions
        FROM wallets w WHERE w.user_id=%s
        """,
        (user_id,),
    )
    if not row:
        raise NotFound("Wallet not found.")
    return row


def top_up_wallet(
    user_id: int,
    amount: Any,
    description: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM top_up_wallet(%s,%s,%s)", (user_id, amount, description))
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=user_id,
            action="wallet.top_up",
            resource_type="wallet",
            resource_id=result["wallet_id"],
            request_id=request_id,
            ip_address=ip_address,
            metadata={"amount": str(amount), "reference_code": result["reference_code"]},
        )
    return result


def create_reservation(
    user_id: int,
    ticket_id: int,
    quantity: int,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        _expire_due(conn)
        cur.execute("SELECT * FROM reserve_ticket(%s,%s,%s)", (user_id, ticket_id, quantity))
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=user_id,
            action="reservation.create",
            resource_type="reservation",
            resource_id=result["reservation_id"],
            request_id=request_id,
            ip_address=ip_address,
            metadata={"ticket_id": ticket_id, "quantity": quantity},
        )
    invalidate_ticket_cache()
    return result


def list_reservations(user_id: int, *, status: str | None, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    with database.transaction() as conn:
        expired = _expire_due(conn)
    if any(expired):
        invalidate_ticket_cache()
    clauses = ["r.user_id=%s"]
    params: list[Any] = [user_id]
    if status:
        clauses.append("r.status=%s")
        params.append(status)
    where = " AND ".join(clauses)
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM reservations r WHERE {where}", tuple(params))
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT r.id,r.status,r.quantity,r.unit_price,r.total_amount,r.reserved_at,
                   r.expires_at,r.paid_at,r.canceled_at,r.cancellation_reason,
                   r.support_review_status,r.support_review_note,r.support_reviewed_at,
                   vc.ticket_id,vc.sport_code,vc.sport_name,vc.home_team,vc.away_team,
                   vc.tournament_name,vc.starts_at,vc.venue_name,vc.city_name,
                   vc.category_name,vc.section_code,vc.row_code,vc.seat_code,
                   EXISTS(SELECT 1 FROM cancellation_requests cr
                          WHERE cr.reservation_id=r.id AND cr.status='pending') AS has_pending_cancellation,
                   EXISTS(SELECT 1 FROM seat_change_requests scr
                          WHERE scr.reservation_id=r.id AND scr.status='pending') AS has_pending_seat_change
            FROM reservations r
            JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
            WHERE {where}
            ORDER BY r.reserved_at DESC,r.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def reservation_detail(user_id: int, reservation_id: int) -> dict[str, Any]:
    with database.transaction() as conn:
        expired = _expire_due(conn)
    if any(expired):
        invalidate_ticket_cache()
    row = database.fetch_one(
        """
        SELECT r.id,r.status,r.quantity,r.unit_price,r.total_amount,r.reserved_at,
               r.expires_at,r.paid_at,r.canceled_at,r.cancellation_reason,
               r.support_review_status,r.support_review_note,r.support_reviewed_at,
               vc.*,
               COALESCE((SELECT jsonb_agg(to_jsonb(p) ORDER BY p.created_at DESC)
                         FROM payments p WHERE p.reservation_id=r.id),'[]'::jsonb) AS payments,
               COALESCE((SELECT jsonb_agg(to_jsonb(it) ORDER BY it.issued_at)
                         FROM issued_tickets it WHERE it.reservation_id=r.id),'[]'::jsonb) AS issued_tickets,
               COALESCE((SELECT jsonb_agg(to_jsonb(h) ORDER BY h.changed_at)
                         FROM reservation_status_history h WHERE h.reservation_id=r.id),'[]'::jsonb) AS status_history
        FROM reservations r
        JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
        WHERE r.id=%s AND r.user_id=%s
        """,
        (reservation_id, user_id),
    )
    if not row:
        raise NotFound("Reservation not found.")
    return row


def pay_reservation(
    user_id: int,
    reservation_id: int,
    payment_method: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        _expire_due(conn)
        cur.execute(
            "SELECT * FROM process_payment(%s,%s,%s)",
            (user_id, reservation_id, payment_method),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=user_id,
            action="reservation.payment",
            resource_type="payment",
            resource_id=result["payment_id"],
            request_id=request_id,
            ip_address=ip_address,
            metadata={
                "reservation_id": reservation_id,
                "status": result["payment_status"],
                "method": payment_method,
            },
        )
    invalidate_ticket_cache()
    return result


def list_payments(user_id: int, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM payments p JOIN reservations r ON r.id=p.reservation_id
            WHERE r.user_id=%s
            """,
            (user_id,),
        )
        total = int(cur.fetchone()["total"])
        cur.execute(
            """
            SELECT p.id,p.reservation_id,p.amount,p.status,p.transaction_ref,
                   p.failure_reason,p.created_at,p.paid_at,pm.code AS method_code,pm.name AS method_name
            FROM payments p
            JOIN reservations r ON r.id=p.reservation_id
            JOIN payment_methods pm ON pm.id=p.payment_method_id
            WHERE r.user_id=%s
            ORDER BY p.created_at DESC,p.id DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, page_size, (page - 1) * page_size),
        )
        return list(cur.fetchall()), total


def list_bookings(user_id: int, scope: str, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    clauses = ["r.user_id=%s", "r.status IN ('paid','refunded')"]
    params: list[Any] = [user_id]
    if scope == "upcoming":
        clauses.extend(["m.starts_at>CURRENT_TIMESTAMP", "r.status='paid'"])
    elif scope == "used":
        clauses.append("EXISTS(SELECT 1 FROM issued_tickets it WHERE it.reservation_id=r.id AND it.status='used')")
    elif scope == "canceled":
        clauses.append("r.status='refunded'")
    elif scope != "all":
        raise ApiError("validation_error", "scope must be all, upcoming, used, or canceled.", 422)
    where = " AND ".join(clauses)
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM reservations r JOIN tickets t ON t.id=r.ticket_id JOIN matches m ON m.id=t.match_id
            WHERE {where}
            """,
            tuple(params),
        )
        total = int(cur.fetchone()["total"])
        cur.execute(
            f"""
            SELECT r.id AS reservation_id,r.status AS reservation_status,r.quantity,
                   r.total_amount,r.paid_at,r.canceled_at,
                   vc.ticket_id,vc.sport_name,vc.home_team,vc.away_team,vc.tournament_name,
                   vc.starts_at,vc.venue_name,vc.city_name,vc.category_name,vc.section_code,
                   vc.row_code,vc.seat_code,
                   COALESCE((SELECT jsonb_agg(jsonb_build_object(
                      'ticket_number',it.ticket_number,'qr_token',it.qr_token,
                      'status',it.status,'issued_at',it.issued_at,'used_at',it.used_at
                   ) ORDER BY it.issued_at) FROM issued_tickets it WHERE it.reservation_id=r.id),'[]'::jsonb) AS tickets
            FROM reservations r
            JOIN tickets t ON t.id=r.ticket_id
            JOIN matches m ON m.id=t.match_id
            JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
            WHERE {where}
            ORDER BY vc.starts_at DESC,r.id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, (page - 1) * page_size]),
        )
        return list(cur.fetchall()), total


def cancellation_quote(user_id: int, reservation_id: int) -> dict[str, Any]:
    row = database.fetch_one(
        """
        SELECT r.id AS reservation_id,r.status,r.total_amount,vc.starts_at,
               fn_get_penalty_percentage(r.ticket_id,CURRENT_TIMESTAMP) AS penalty_percentage,
               ROUND(r.total_amount*(100-fn_get_penalty_percentage(r.ticket_id,CURRENT_TIMESTAMP))/100,2) AS estimated_refund
        FROM reservations r
        JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
        WHERE r.id=%s AND r.user_id=%s AND r.status='paid'
        """,
        (reservation_id, user_id),
    )
    if not row:
        raise NotFound("Paid reservation not found.")
    return row


def request_cancellation(
    user_id: int,
    reservation_id: int,
    reason: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM request_cancellation(%s,%s,%s)",
            (user_id, reservation_id, reason),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=user_id,
            action="cancellation.request",
            resource_type="cancellation_request",
            resource_id=result["request_id"],
            request_id=request_id,
            ip_address=ip_address,
            metadata={"reservation_id": reservation_id},
        )
    return result


def request_seat_change(
    user_id: int,
    reservation_id: int,
    new_ticket_id: int,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        _expire_due(conn)
        cur.execute(
            "SELECT request_seat_change(%s,%s,%s) AS request_id",
            (user_id, reservation_id, new_ticket_id),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=user_id,
            action="seat_change.request",
            resource_type="seat_change_request",
            resource_id=result["request_id"],
            request_id=request_id,
            ip_address=ip_address,
            metadata={"reservation_id": reservation_id, "new_ticket_id": new_ticket_id},
        )
    invalidate_ticket_cache()
    return result


def create_report(
    user_id: int,
    *,
    ticket_id: int | None,
    reservation_id: int | None,
    payment_id: int | None,
    category_id: int,
    subject: str,
    description: str,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO reports
                (reporter_id,ticket_id,reservation_id,payment_id,category_id,subject,description,status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')
            RETURNING id,status,created_at
            """,
            (user_id, ticket_id, reservation_id, payment_id, category_id, subject, description),
        )
        result = cur.fetchone()
        audit(
            conn,
            actor_user_id=user_id,
            action="report.create",
            resource_type="report",
            resource_id=result["id"],
            request_id=request_id,
            ip_address=ip_address,
            metadata={"category_id": category_id},
        )
    return result


def list_reports(user_id: int, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    with database.transaction(read_only=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM reports WHERE reporter_id=%s", (user_id,))
        total = int(cur.fetchone()["total"])
        cur.execute(
            """
            SELECT rp.id,rp.ticket_id,rp.reservation_id,rp.payment_id,rp.subject,
                   rp.description,rp.status,rp.support_response,rp.created_at,rp.updated_at,
                   rp.resolved_at,rc.code AS category_code,rc.name AS category_name,
                   su.first_name AS support_first_name,su.last_name AS support_last_name
            FROM reports rp
            JOIN report_categories rc ON rc.id=rp.category_id
            LEFT JOIN users su ON su.id=rp.assigned_to
            WHERE rp.reporter_id=%s
            ORDER BY rp.created_at DESC,rp.id DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, page_size, (page - 1) * page_size),
        )
        return list(cur.fetchall()), total


def issued_tickets(user_id: int) -> list[dict[str, Any]]:
    return database.fetch_all(
        """
        SELECT it.id,it.ticket_number,it.qr_token,it.status,it.issued_at,it.used_at,
               r.id AS reservation_id,vc.sport_name,vc.home_team,vc.away_team,
               vc.starts_at,vc.venue_name,vc.category_name,vc.section_code,vc.row_code,vc.seat_code
        FROM issued_tickets it
        JOIN reservations r ON r.id=it.reservation_id
        JOIN v_ticket_catalog vc ON vc.ticket_id=r.ticket_id
        WHERE r.user_id=%s
        ORDER BY vc.starts_at DESC,it.issued_at DESC
        """,
        (user_id,),
    )
