"""HTTP API views. Each endpoint performs one focused task."""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from django.http import HttpRequest, JsonResponse

import cache
import database
import services_auth
import services_catalog
import services_reservations
import services_support
import services_chat
import search_engine
import notifications
from authentication import OtpService, TokenService, client_ip, endpoint
from config import config
from exceptions import ApiError, PermissionDenied
from responses import error, ok
from version import SERVICE_NAME, VERSION
from validators import (
    body,
    boolean,
    date_value,
    datetime_value,
    decimal_number,
    email,
    integer,
    password,
    phone,
    required,
    text,
    url,
    optional_query_text,
    ensure_allowed_fields,
    ensure_allowed_query_params,
)

RESERVATION_STATUSES = {"held", "paid", "canceled", "expired", "refunded"}
REQUEST_STATUSES = {"pending", "approved", "rejected", "processed"}
SEAT_CHANGE_STATUSES = {"pending", "rejected", "processed", "expired"}
REPORT_STATUSES = {"pending", "in_review", "resolved", "rejected"}
SUPPORT_REVIEW_STATUSES = {"not_reviewed", "verified", "needs_correction"}
CHAT_STATUSES = {"open", "closed"}


def _principal(request: HttpRequest) -> Any:
    return request.principal  


def _request_id(request: HttpRequest) -> str | None:
    return getattr(request, "request_id", None)


def _pagination(request: HttpRequest) -> tuple[int, int]:
    page = integer(request.GET.get("page", 1), "page", minimum=1)
    page_size = integer(request.GET.get("page_size", 20), "page_size", minimum=1, maximum=100)
    return page, page_size


def _meta(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": math.ceil(total / page_size) if total else 0,
    }


def _optional_int(value: Any, name: str) -> int | None:
    return None if value in (None, "") else integer(value, name, minimum=1)


def _optional_decimal(value: Any, name: str) -> Decimal | None:
    return None if value in (None, "") else decimal_number(value, name, minimum=Decimal("0"))


def _optional_bool(value: Any, name: str) -> bool | None:
    return None if value in (None, "") else boolean(value, name)


def _strict_body(request: HttpRequest, allowed: set[str]) -> dict[str, Any]:
    return ensure_allowed_fields(body(request), allowed)


def _strict_query(request: HttpRequest, allowed: set[str]) -> None:
    ensure_allowed_query_params(request, allowed)


@endpoint({"GET"}, auth=False)
def health(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok({"status": "ok", "service": SERVICE_NAME, "version": VERSION})


@endpoint({"GET"}, auth=False)
def ready(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    db_ok = database.ping()
    redis_ok = cache.ping()
    elasticsearch_reachable = (
        search_engine.ping() if config.elasticsearch_enabled else True
    )
    elasticsearch_index_ready = (
        search_engine.index_ready()
        if config.elasticsearch_enabled and elasticsearch_reachable
        else not config.elasticsearch_enabled
    )
    email_ok, email_status = (
        notifications.email_transport_status()
        if config.otp_email_enabled
        else (False, "OTP email delivery is disabled.")
    )
    dependencies_ok = (
        db_ok
        and (redis_ok or not config.redis_required)
        and elasticsearch_reachable
        and elasticsearch_index_ready
        and (email_ok or not config.otp_email_required)
    )
    details = {
        "database": db_ok,
        "redis": redis_ok,
        "redis_required": config.redis_required,
        "elasticsearch": elasticsearch_reachable,
        "elasticsearch_index_ready": elasticsearch_index_ready,
        "elasticsearch_enabled": config.elasticsearch_enabled,
        "otp_email_enabled": config.otp_email_enabled,
        "otp_email_required": config.otp_email_required,
        "email_transport": email_ok,
        "email_transport_status": email_status,
    }
    if dependencies_ok:
        return ok({"status": "ready", **details})
    return error(
        "service_not_ready",
        "One or more required dependencies are unavailable.",
        status=503,
        details=details,
        request_id=_request_id(request),
    )


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def auth_capabilities(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    email_ok, email_status = (
        notifications.email_transport_status()
        if config.otp_email_enabled
        else (False, "OTP email delivery is disabled.")
    )
    return ok(
        {
            "password_login": True,
            "signup": True,
            "otp": {
                "email": bool(config.otp_email_enabled and email_ok),
                "phone": bool(config.otp_sms_webhook_url),
            },
            "email_transport": {
                "configured": config.otp_email_enabled,
                "ready": email_ok,
                "status": email_status,
                "mode": config.email_delivery_mode,
            },
            "local_mailbox_url": (
                config.public_mailpit_url
                if config.email_delivery_mode == "mailpit_api"
                else None
            ),
        }
    )


@endpoint({"POST"}, auth=False, rate_limit=(10, 3600))
def signup(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"first_name", "last_name", "email", "phone", "password", "preferred_login", "city_id", "date_of_birth"})
    first_name = text(required(data, "first_name"), "first_name", min_len=1, max_len=100)
    last_name = text(required(data, "last_name"), "last_name", min_len=1, max_len=100)
    email_value = email(data.get("email"), allow_none=True)
    phone_value = phone(data.get("phone"), allow_none=True)
    preferred_default = "email" if email_value else "phone"
    preferred = text(
        data.get("preferred_login", preferred_default),
        "preferred_login",
        min_len=5,
        max_len=5,
    )
    password_value = password(required(data, "password"))
    city_id = _optional_int(data.get("city_id"), "city_id")
    birth = date_value(data.get("date_of_birth"), "date_of_birth", allow_none=True)
    result = services_auth.request_signup(
        first_name=first_name or "",
        last_name=last_name or "",
        email=email_value,
        phone=phone_value,
        password=password_value,
        preferred_login=preferred or "email",
        city_id=city_id,
        date_of_birth=birth,
        ip_address=client_ip(request),
    )
    return ok(result, status=202)


@endpoint({"POST"}, auth=False, rate_limit=(10, 600))
def signup_resend(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"registration_id"})
    registration_id = text(
        required(data, "registration_id"),
        "registration_id",
        min_len=32,
        max_len=32,
    )
    result = services_auth.resend_signup_otp(
        registration_id or "",
        ip_address=client_ip(request),
    )
    return ok(result, status=202)


@endpoint({"POST"}, auth=False, rate_limit=(20, 600))
def signup_verify(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"registration_id", "code"})
    registration_id = text(
        required(data, "registration_id"),
        "registration_id",
        min_len=32,
        max_len=32,
    )
    code = text(required(data, "code"), "code", min_len=6, max_len=6)
    user, tokens = services_auth.verify_signup(
        registration_id or "",
        code or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok({"user": user, "tokens": tokens}, status=201)


@endpoint({"POST"}, auth=False, rate_limit=(10, 300))
def password_login(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"contact", "password"})
    contact = text(required(data, "contact"), "contact", min_len=3, max_len=254)
    password_value = text(required(data, "password"), "password", min_len=1, max_len=128)
    user, tokens = services_auth.password_login(contact or "", password_value or "")
    return ok({"user": user, "tokens": tokens})


@endpoint({"POST"}, auth=False, rate_limit=(10, 300))
def otp_request(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"contact"})
    contact = text(required(data, "contact"), "contact", min_len=3, max_len=254)
    return ok(services_auth.request_login_otp(contact or "", client_ip(request)), status=202)


@endpoint({"POST"}, auth=False, rate_limit=(20, 300))
def otp_verify(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"contact", "code"})
    contact = text(required(data, "contact"), "contact", min_len=3, max_len=254)
    code = text(required(data, "code"), "code", min_len=6, max_len=6)
    user, tokens = services_auth.otp_login(contact or "", code or "")
    return ok({"user": user, "tokens": tokens})


@endpoint({"POST"}, auth=False, rate_limit=(30, 300))
def token_refresh(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"refresh_token"})
    refresh = text(required(data, "refresh_token"), "refresh_token", min_len=20, max_len=4096)
    tokens, user = TokenService.rotate_refresh(refresh or "")
    return ok({"user": user, "tokens": tokens})


@endpoint({"POST"}, auth=True)
def logout(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"refresh_token"})
    refresh = data.get("refresh_token")
    if refresh is not None:
        refresh = text(refresh, "refresh_token", min_len=20, max_len=4096)
    TokenService.revoke(getattr(request, "access_token", None), refresh)
    return ok({"logged_out": True})


@endpoint({"GET", "PATCH"}, auth=True)
def profile(request: HttpRequest) -> JsonResponse:
    user_id = _principal(request).id
    if request.method == "GET":
        _strict_query(request, set())
        return ok(services_auth.get_profile(user_id))
    data = _strict_body(request, {"first_name", "last_name", "city_id", "date_of_birth", "profile_picture_url"})
    fields: dict[str, Any] = {}
    if "first_name" in data:
        fields["first_name"] = text(data["first_name"], "first_name", min_len=1, max_len=100)
    if "last_name" in data:
        fields["last_name"] = text(data["last_name"], "last_name", min_len=1, max_len=100)
    if "city_id" in data:
        fields["city_id"] = _optional_int(data["city_id"], "city_id")
    if "date_of_birth" in data:
        fields["date_of_birth"] = date_value(data["date_of_birth"], "date_of_birth", allow_none=True)
    if "profile_picture_url" in data:
        fields["profile_picture_url"] = url(
            data["profile_picture_url"], "profile_picture_url", allow_none=True
        )
    result = services_auth.update_profile(
        user_id,
        fields,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"POST"}, auth=True, rate_limit=(5, 600))
def profile_password_otp_request(request: HttpRequest) -> JsonResponse:
    _strict_body(request, set())
    result = services_auth.request_password_change_otp(
        _principal(request).id, client_ip(request)
    )
    return ok(result, status=202)


@endpoint({"POST"}, auth=True, rate_limit=(5, 3600))
def profile_password_change(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"current_password", "new_password", "code"})
    current_password = text(required(data, "current_password"), "current_password", min_len=1, max_len=128)
    new_password = password(required(data, "new_password"), "new_password")
    code = text(required(data, "code"), "code", min_len=6, max_len=6)
    result = services_auth.change_password(
        _principal(request).id,
        current_password or "",
        new_password,
        code or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok({"changed": True, **result})


@endpoint({"POST"}, auth=True, rate_limit=(5, 600))
def profile_contact_request(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"contact"})
    contact = text(required(data, "contact"), "contact", min_len=3, max_len=254)
    result = services_auth.request_contact_change(_principal(request).id, contact or "", client_ip(request))
    return ok(result, status=202)


@endpoint({"POST"}, auth=True, rate_limit=(10, 600))
def profile_contact_confirm(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"contact", "code", "preferred_login"})
    contact = text(required(data, "contact"), "contact", min_len=3, max_len=254)
    code = text(required(data, "code"), "code", min_len=6, max_len=6)
    preferred = text(required(data, "preferred_login"), "preferred_login", min_len=5, max_len=5)
    result = services_auth.confirm_contact_change(
        _principal(request).id,
        contact or "",
        code or "",
        preferred or "email",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def cities(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.cities())


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def venues(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"city_id"})
    city_id = _optional_int(request.GET.get("city_id"), "city_id")
    return ok(services_catalog.venues(city_id))


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def sports(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.sports())


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def ticket_categories(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.ticket_categories())


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def payment_methods(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.payment_methods())


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def report_categories(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.report_categories())


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def amenities(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.amenities())


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def matches(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"upcoming_only"})
    upcoming_only = _optional_bool(request.GET.get("upcoming_only", "true"), "upcoming_only")
    return ok(services_catalog.matches(upcoming_only=True if upcoming_only is None else upcoming_only))


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def tickets_search(request: HttpRequest) -> JsonResponse:
    _strict_query(
        request,
        {
            "page", "page_size", "q", "sport", "team", "city_id",
            "venue_id", "category", "section", "date_from", "date_to",
            "price_min", "price_max", "min_available", "numbered",
            "ordering",
        },
    )
    page, page_size = _pagination(request)
    filters: dict[str, Any] = {
        "q": optional_query_text(request.GET.get("q"), "q", max_len=200),
        "sport": optional_query_text(request.GET.get("sport"), "sport", max_len=100),
        "team": optional_query_text(request.GET.get("team"), "team", max_len=200),
        "city_id": _optional_int(request.GET.get("city_id"), "city_id"),
        "venue_id": _optional_int(request.GET.get("venue_id"), "venue_id"),
        "category": optional_query_text(
            request.GET.get("category"), "category", max_len=100
        ),
        "section": optional_query_text(
            request.GET.get("section"), "section", max_len=50
        ),
        "date_from": datetime_value(request.GET.get("date_from"), "date_from", allow_none=True),
        "date_to": datetime_value(request.GET.get("date_to"), "date_to", allow_none=True),
        "price_min": _optional_decimal(request.GET.get("price_min"), "price_min"),
        "price_max": _optional_decimal(request.GET.get("price_max"), "price_max"),
        "min_available": _optional_int(request.GET.get("min_available"), "min_available"),
        "numbered": _optional_bool(request.GET.get("numbered"), "numbered"),
        "ordering": optional_query_text(
            request.GET.get("ordering", "starts_at"), "ordering", max_len=30
        )
        or "starts_at",
    }
    if filters["price_min"] is not None and filters["price_max"] is not None and filters["price_min"] > filters["price_max"]:
        raise ApiError("validation_error", "price_min cannot exceed price_max.", 422)
    if filters["date_from"] is not None and filters["date_to"] is not None and filters["date_from"] > filters["date_to"]:
        raise ApiError("validation_error", "date_from cannot exceed date_to.", 422)
    items, total = services_catalog.search_tickets(filters, page=page, page_size=page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"GET"}, auth=False, rate_limit=(120, 60))
def ticket_detail(request: HttpRequest, ticket_id: int) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_catalog.ticket_detail(ticket_id))


@endpoint({"GET"}, auth=True, roles={"spectator"})
def wallet(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_reservations.wallet(_principal(request).id))


@endpoint({"POST"}, auth=True, roles={"spectator"}, rate_limit=(20, 3600))
def wallet_top_up(request: HttpRequest) -> JsonResponse:
    if not config.allow_local_wallet_top_up:
        raise PermissionDenied(
            "Local wallet top-up is disabled outside the demonstration environment."
        )
    data = _strict_body(request, {"amount", "description"})
    amount = decimal_number(required(data, "amount"), "amount", minimum=Decimal("1"), maximum=Decimal("100000000000"))
    description = text(data.get("description", "Wallet top-up"), "description", min_len=1, max_len=500)
    result = services_reservations.top_up_wallet(
        _principal(request).id,
        amount,
        description or "Wallet top-up",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"GET", "POST"}, auth=True, roles={"spectator"})
def reservations(request: HttpRequest) -> JsonResponse:
    user_id = _principal(request).id
    if request.method == "GET":
        _strict_query(request, {"page", "page_size", "status"})
        page, page_size = _pagination(request)
        status = request.GET.get("status") or None
        if status and status not in RESERVATION_STATUSES:
            raise ApiError("validation_error", "Invalid reservation status.", 422)
        items, total = services_reservations.list_reservations(user_id, status=status, page=page, page_size=page_size)
        return ok(items, meta=_meta(page, page_size, total))
    data = _strict_body(request, {"ticket_id", "quantity"})
    ticket_id = integer(required(data, "ticket_id"), "ticket_id", minimum=1)
    quantity = integer(data.get("quantity", 1), "quantity", minimum=1, maximum=20)
    result = services_reservations.create_reservation(
        user_id,
        ticket_id,
        quantity,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"GET"}, auth=True, roles={"spectator"})
def reservation_detail(request: HttpRequest, reservation_id: int) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_reservations.reservation_detail(_principal(request).id, reservation_id))


@endpoint({"POST"}, auth=True, roles={"spectator"}, rate_limit=(20, 300))
def reservation_pay(request: HttpRequest, reservation_id: int) -> JsonResponse:
    data = _strict_body(request, {"payment_method"})
    method = text(required(data, "payment_method"), "payment_method", min_len=1, max_len=50)
    result = services_reservations.pay_reservation(
        _principal(request).id,
        reservation_id,
        method or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    if result["payment_status"] != "successful":
        return error(
            "payment_failed",
            result.get("failure_reason") or "Payment could not be completed.",
            status=409,
            details=result,
            request_id=_request_id(request),
        )
    return ok(result)


@endpoint({"GET"}, auth=True, roles={"spectator"})
def payments(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size"})
    page, page_size = _pagination(request)
    items, total = services_reservations.list_payments(_principal(request).id, page, page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"GET"}, auth=True, roles={"spectator"})
def bookings(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size", "scope"})
    page, page_size = _pagination(request)
    scope = request.GET.get("scope", "all")
    items, total = services_reservations.list_bookings(_principal(request).id, scope, page, page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"GET"}, auth=True, roles={"spectator"})
def cancellation_quote(request: HttpRequest, reservation_id: int) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_reservations.cancellation_quote(_principal(request).id, reservation_id))


@endpoint({"POST"}, auth=True, roles={"spectator"})
def cancellation_request(request: HttpRequest, reservation_id: int) -> JsonResponse:
    data = _strict_body(request, {"reason"})
    reason = text(required(data, "reason"), "reason", min_len=3, max_len=2000)
    result = services_reservations.request_cancellation(
        _principal(request).id,
        reservation_id,
        reason or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"GET"}, auth=True, roles={"spectator"})
def seat_change_options(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"reservation_id"})
    reservation_id = integer(required(request.GET, "reservation_id"), "reservation_id", minimum=1)
    return ok(services_catalog.seat_change_options(_principal(request).id, reservation_id))


@endpoint({"POST"}, auth=True, roles={"spectator"})
def seat_change_request(request: HttpRequest, reservation_id: int) -> JsonResponse:
    data = _strict_body(request, {"new_ticket_id"})
    new_ticket_id = integer(required(data, "new_ticket_id"), "new_ticket_id", minimum=1)
    result = services_reservations.request_seat_change(
        _principal(request).id,
        reservation_id,
        new_ticket_id,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"GET", "POST"}, auth=True, roles={"spectator"})
def reports(request: HttpRequest) -> JsonResponse:
    user_id = _principal(request).id
    if request.method == "GET":
        _strict_query(request, {"page", "page_size"})
        page, page_size = _pagination(request)
        items, total = services_reservations.list_reports(user_id, page, page_size)
        return ok(items, meta=_meta(page, page_size, total))
    data = _strict_body(request, {"ticket_id", "reservation_id", "payment_id", "category_id", "subject", "description"})
    ticket_id = _optional_int(data.get("ticket_id"), "ticket_id")
    reservation_id = _optional_int(data.get("reservation_id"), "reservation_id")
    payment_id = _optional_int(data.get("payment_id"), "payment_id")
    if not any((ticket_id, reservation_id, payment_id)):
        raise ApiError("validation_error", "At least one report target is required.", 422)
    category_id = integer(required(data, "category_id"), "category_id", minimum=1)
    subject = text(required(data, "subject"), "subject", min_len=3, max_len=200)
    description = text(required(data, "description"), "description", min_len=5, max_len=5000)
    result = services_reservations.create_report(
        user_id,
        ticket_id=ticket_id,
        reservation_id=reservation_id,
        payment_id=payment_id,
        category_id=category_id,
        subject=subject or "",
        description=description or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"GET"}, auth=True, roles={"spectator"})
def issued_tickets(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_reservations.issued_tickets(_principal(request).id))


@endpoint({"GET"}, auth=True, roles={"spectator"})
def support_chat(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"after_id", "limit", "mark_read"})
    after_id = integer(request.GET.get("after_id", 0), "after_id", minimum=0)
    limit = integer(request.GET.get("limit", 100), "limit", minimum=1, maximum=100)
    mark_read = _optional_bool(request.GET.get("mark_read"), "mark_read") or False
    return ok(services_chat.get_spectator_chat(
        _principal(request).id,
        after_id=after_id,
        limit=limit,
        mark_read=mark_read,
    ))


@endpoint({"POST"}, auth=True, roles={"spectator"}, rate_limit=(30, 60))
def support_chat_message(request: HttpRequest) -> JsonResponse:
    data = _strict_body(request, {"body"})
    message = text(required(data, "body"), "body", min_len=1, max_len=2000)
    result = services_chat.send_spectator_message(
        _principal(request).id,
        message or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"POST"}, auth=True, roles={"spectator"})
def support_chat_read(request: HttpRequest) -> JsonResponse:
    _strict_body(request, set())
    return ok(services_chat.mark_spectator_read(_principal(request).id))


@endpoint({"GET"}, auth=True, roles={"support"})
def support_dashboard(request: HttpRequest) -> JsonResponse:
    _strict_query(request, set())
    return ok(services_support.dashboard())


@endpoint({"GET"}, auth=True, roles={"support"})
def support_reservations(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size", "status", "user_id", "review_status"})
    page, page_size = _pagination(request)
    status = request.GET.get("status") or None
    if status and status not in RESERVATION_STATUSES:
        raise ApiError("validation_error", "Invalid reservation status.", 422)
    user_id = _optional_int(request.GET.get("user_id"), "user_id")
    review_status = request.GET.get("review_status") or None
    if review_status and review_status not in SUPPORT_REVIEW_STATUSES:
        raise ApiError("validation_error", "Invalid support review status.", 422)
    items, total = services_support.list_reservations(
        status=status,
        user_id=user_id,
        review_status=review_status,
        page=page,
        page_size=page_size,
    )
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"POST"}, auth=True, roles={"support"})
def support_reservation_review(request: HttpRequest, reservation_id: int) -> JsonResponse:
    data = _strict_body(request, {"review_status", "note"})
    review_status = text(
        required(data, "review_status"), "review_status", min_len=8, max_len=30
    )
    note = text(data.get("note"), "note", max_len=2000, allow_none=True)
    result = services_support.review_reservation(
        _principal(request).id,
        reservation_id,
        review_status or "",
        note,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"POST"}, auth=True, roles={"support"})
def support_reservation_seat_correction(
    request: HttpRequest, reservation_id: int
) -> JsonResponse:
    data = _strict_body(request, {"new_ticket_id", "note"})
    new_ticket_id = integer(required(data, "new_ticket_id"), "new_ticket_id", minimum=1)
    note = text(required(data, "note"), "note", min_len=3, max_len=2000)
    result = services_support.correct_reservation_seat(
        _principal(request).id,
        reservation_id,
        new_ticket_id,
        note or "Seat correction approved by support",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"POST"}, auth=True, roles={"support"})
def support_reservation_cancel(request: HttpRequest, reservation_id: int) -> JsonResponse:
    data = _strict_body(request, {"reason"})
    reason = text(required(data, "reason"), "reason", min_len=3, max_len=2000)
    result = services_support.cancel_held_reservation(
        _principal(request).id,
        reservation_id,
        reason or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"GET"}, auth=True, roles={"support"})
def support_suspicious_payments(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size"})
    page, page_size = _pagination(request)
    items, total = services_support.suspicious_payments(page, page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"GET"}, auth=True, roles={"support"})
def support_cancellation_requests(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size", "status"})
    page, page_size = _pagination(request)
    status = request.GET.get("status") or None
    if status and status not in REQUEST_STATUSES:
        raise ApiError("validation_error", "Invalid cancellation request status.", 422)
    items, total = services_support.list_cancellation_requests(status, page, page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"POST"}, auth=True, roles={"support"})
def support_cancellation_review(request: HttpRequest, request_id_value: int) -> JsonResponse:
    data = _strict_body(request, {"approve", "note"})
    approve = boolean(required(data, "approve"), "approve")
    note = text(data.get("note"), "note", max_len=2000, allow_none=True)
    result = services_support.review_cancellation(
        _principal(request).id,
        request_id_value,
        approve,
        note,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"GET"}, auth=True, roles={"support"})
def support_seat_change_requests(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size", "status"})
    page, page_size = _pagination(request)
    status = request.GET.get("status") or None
    if status and status not in SEAT_CHANGE_STATUSES:
        raise ApiError("validation_error", "Invalid seat-change request status.", 422)
    items, total = services_support.list_seat_change_requests(status, page, page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"POST"}, auth=True, roles={"support"})
def support_seat_change_review(request: HttpRequest, request_id_value: int) -> JsonResponse:
    data = _strict_body(request, {"approve", "note"})
    approve = boolean(required(data, "approve"), "approve")
    note = text(data.get("note"), "note", max_len=2000, allow_none=True)
    result = services_support.review_seat_change(
        _principal(request).id,
        request_id_value,
        approve,
        note,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"GET"}, auth=True, roles={"support"})
def support_reports(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size", "status"})
    page, page_size = _pagination(request)
    status = request.GET.get("status") or None
    if status and status not in REPORT_STATUSES:
        raise ApiError("validation_error", "Invalid report status.", 422)
    items, total = services_support.list_reports(status, page, page_size)
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"PATCH"}, auth=True, roles={"support"})
def support_report_update(request: HttpRequest, report_id: int) -> JsonResponse:
    data = _strict_body(request, {"status", "response"})
    status = text(required(data, "status"), "status", min_len=7, max_len=20)
    response = text(data.get("response"), "response", max_len=5000, allow_none=True)
    result = services_support.update_report(
        _principal(request).id,
        report_id,
        status=status or "",
        response=response,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"POST"}, auth=True, roles={"support"})
def support_user_deactivate(request: HttpRequest, user_id: int) -> JsonResponse:
    data = _strict_body(request, {"reason"})
    reason = text(data.get("reason", "Account deactivated by support"), "reason", min_len=3, max_len=2000)
    result = services_support.deactivate_user(
        _principal(request).id,
        user_id,
        reason or "Account deactivated by support",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


def _ticket_payload(data: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    result: dict[str, Any] = {}
    required_fields = [] if partial else [
        "match_id", "ticket_category_id", "section_code", "is_numbered", "price", "total_capacity"
    ]
    for name in required_fields:
        required(data, name)
    if "match_id" in data:
        result["match_id"] = integer(data["match_id"], "match_id", minimum=1)
    if "ticket_category_id" in data:
        result["ticket_category_id"] = integer(data["ticket_category_id"], "ticket_category_id", minimum=1)
    if "section_code" in data:
        result["section_code"] = text(data["section_code"], "section_code", min_len=1, max_len=50)
    if "row_code" in data:
        result["row_code"] = text(data["row_code"], "row_code", max_len=50, allow_none=True)
    if "seat_code" in data:
        result["seat_code"] = text(data["seat_code"], "seat_code", max_len=50, allow_none=True)
    if "is_numbered" in data:
        result["is_numbered"] = boolean(data["is_numbered"], "is_numbered")
    if "price" in data:
        result["price"] = decimal_number(data["price"], "price", minimum=Decimal("0"))
    if "total_capacity" in data:
        result["total_capacity"] = integer(data["total_capacity"], "total_capacity", minimum=1)
    if "sale_starts_at" in data:
        result["sale_starts_at"] = datetime_value(data["sale_starts_at"], "sale_starts_at", allow_none=True)
    if "sale_ends_at" in data:
        result["sale_ends_at"] = datetime_value(data["sale_ends_at"], "sale_ends_at", allow_none=True)
    if "is_active" in data:
        result["is_active"] = boolean(data["is_active"], "is_active")
    if "amenity_ids" in data:
        if not isinstance(data["amenity_ids"], list):
            raise ApiError("validation_error", "amenity_ids must be an array.", 422)
        if len(data["amenity_ids"]) > 100:
            raise ApiError("validation_error", "amenity_ids cannot contain more than 100 items.", 422)
        parsed = [integer(x, "amenity_ids[]", minimum=1) for x in data["amenity_ids"]]
        result["amenity_ids"] = list(dict.fromkeys(parsed))
    return result


@endpoint({"GET"}, auth=True, roles={"support"})
def support_chats(request: HttpRequest) -> JsonResponse:
    _strict_query(request, {"page", "page_size", "status"})
    page, page_size = _pagination(request)
    status = request.GET.get("status") or None
    if status and status not in CHAT_STATUSES:
        raise ApiError("validation_error", "Invalid chat status.", 422)
    items, total = services_chat.list_support_conversations(
        status=status, page=page, page_size=page_size
    )
    return ok(items, meta=_meta(page, page_size, total))


@endpoint({"GET"}, auth=True, roles={"support"})
def support_chat_detail(request: HttpRequest, conversation_id: int) -> JsonResponse:
    _strict_query(request, {"after_id", "limit", "mark_read"})
    after_id = integer(request.GET.get("after_id", 0), "after_id", minimum=0)
    limit = integer(request.GET.get("limit", 100), "limit", minimum=1, maximum=100)
    mark_read_value = _optional_bool(request.GET.get("mark_read"), "mark_read")
    result = services_chat.get_support_conversation(
        _principal(request).id,
        conversation_id,
        after_id=after_id,
        limit=limit,
        mark_read=True if mark_read_value is None else mark_read_value,
    )
    return ok(result)


@endpoint({"POST"}, auth=True, roles={"support"}, rate_limit=(60, 60))
def support_chat_reply(request: HttpRequest, conversation_id: int) -> JsonResponse:
    data = _strict_body(request, {"body"})
    message = text(required(data, "body"), "body", min_len=1, max_len=2000)
    result = services_chat.send_support_message(
        _principal(request).id,
        conversation_id,
        message or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"PATCH"}, auth=True, roles={"support"})
def support_chat_status(request: HttpRequest, conversation_id: int) -> JsonResponse:
    data = _strict_body(request, {"status"})
    status = text(required(data, "status"), "status", min_len=4, max_len=10)
    result = services_chat.set_conversation_status(
        _principal(request).id,
        conversation_id,
        status or "",
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)


@endpoint({"GET", "POST"}, auth=True, roles={"support"})
def support_tickets(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        _strict_query(request, {"page", "page_size", "include_inactive"})
        page, page_size = _pagination(request)
        include_inactive = _optional_bool(request.GET.get("include_inactive", "true"), "include_inactive")
        items, total = services_support.list_tickets(page, page_size, include_inactive=True if include_inactive is None else include_inactive)
        return ok(items, meta=_meta(page, page_size, total))
    data = _ticket_payload(_strict_body(request, {"match_id", "ticket_category_id", "section_code", "row_code", "seat_code", "is_numbered", "price", "total_capacity", "sale_starts_at", "sale_ends_at", "is_active", "amenity_ids"}), partial=False)
    result = services_support.create_ticket(
        _principal(request).id,
        data,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result, status=201)


@endpoint({"PATCH", "DELETE"}, auth=True, roles={"support"})
def support_ticket_detail(request: HttpRequest, ticket_id: int) -> JsonResponse:
    _strict_query(request, set())
    if request.method == "DELETE":
        if request.body not in (b"", None):
            _strict_body(request, set())
        result = services_support.deactivate_ticket(
            _principal(request).id,
            ticket_id,
            request_id=_request_id(request),
            ip_address=client_ip(request),
        )
        return ok(result)
    data = _ticket_payload(_strict_body(request, {"ticket_category_id", "section_code", "row_code", "seat_code", "is_numbered", "price", "total_capacity", "sale_starts_at", "sale_ends_at", "is_active", "amenity_ids"}), partial=True)
    result = services_support.update_ticket(
        _principal(request).id,
        ticket_id,
        data,
        request_id=_request_id(request),
        ip_address=client_ip(request),
    )
    return ok(result)



def bad_request_handler(request: HttpRequest, exception: Exception) -> JsonResponse:
    del exception
    return error(
        "bad_request",
        "The request could not be processed.",
        status=400,
        request_id=_request_id(request),
    )


def permission_denied_handler(request: HttpRequest, exception: Exception) -> JsonResponse:
    del exception
    return error(
        "permission_denied",
        "You do not have permission for this operation.",
        status=403,
        request_id=_request_id(request),
    )


def not_found_handler(request: HttpRequest, exception: Exception) -> JsonResponse:
    del exception
    return error(
        "not_found",
        "API endpoint not found.",
        status=404,
        request_id=_request_id(request),
    )


def server_error_handler(request: HttpRequest) -> JsonResponse:
    return error(
        "internal_error",
        "An unexpected server error occurred.",
        status=500,
        request_id=_request_id(request),
    )
