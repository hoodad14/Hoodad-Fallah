"""JWT, OTP, request authentication, authorization and endpoint protection."""
from __future__ import annotations

import functools
import hashlib
import hmac
import ipaddress
import logging
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, ParamSpec, TypeVar

import jwt
import redis
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from psycopg import Error as PsycopgError

import cache
import database
from config import config
from exceptions import ApiError, AuthenticationError, PermissionDenied, map_database_error
from notifications import NotificationDeliveryError, deliver_otp
from responses import error

logger = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R", bound=HttpResponse)


@dataclass(frozen=True, slots=True)
class Principal:
    id: int
    role: str
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    session_version: int


class TokenService:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _session_version(user: dict[str, Any]) -> int:
        if "session_version" in user:
            return int(user["session_version"])
        row = database.fetch_one(
            "SELECT session_version FROM users WHERE id=%s", (int(user["id"]),)
        )
        if not row:
            raise AuthenticationError("Account no longer exists.")
        return int(row["session_version"])

    @classmethod
    def _encode(cls, claims: dict[str, Any]) -> str:
        return jwt.encode(claims, config.jwt_secret, algorithm="HS256")

    @classmethod
    def issue_pair(cls, user: dict[str, Any], *, family: str | None = None) -> dict[str, Any]:
        now = cls._now()
        family = family or str(uuid.uuid4())
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())
        user_id = int(user["id"])
        session_version = cls._session_version(user)
        common = {
            "iss": config.jwt_issuer,
            "aud": config.jwt_audience,
            "sub": str(user_id),
            "role": user["role"],
            "sv": session_version,
            "iat": int(now.timestamp()),
        }
        access_exp = now + timedelta(minutes=config.access_token_minutes)
        refresh_exp = now + timedelta(days=config.refresh_token_days)
        access = cls._encode({**common, "jti": access_jti, "type": "access", "exp": access_exp})
        refresh = cls._encode(
            {
                **common,
                "jti": refresh_jti,
                "family": family,
                "type": "refresh",
                "exp": refresh_exp,
            }
        )
        refresh_ttl = max(1, int((refresh_exp - now).total_seconds()))
        cache.store_refresh_token(user_id, refresh_jti, family, refresh_ttl)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "Bearer",
            "access_expires_in": config.access_token_minutes * 60,
            "refresh_expires_in": config.refresh_token_days * 86400,
        }

    @classmethod
    def decode(cls, token: str, expected_type: str) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                config.jwt_secret,
                algorithms=["HS256"],
                issuer=config.jwt_issuer,
                audience=config.jwt_audience,
                options={"require": ["exp", "iat", "jti", "sub", "type", "role", "sv"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired.") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Token is invalid.") from exc
        if claims.get("type") != expected_type:
            raise AuthenticationError("Wrong token type.")
        if expected_type == "access" and cache.client().exists(f"blacklist:{claims['jti']}"):
            raise AuthenticationError("Token has been revoked.")
        return claims

    @classmethod
    def _revoke_family(cls, family: str) -> None:
        cache.revoke_refresh_family(family)

    @classmethod
    def rotate_refresh(cls, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
        claims = cls.decode(token, "refresh")
        user_id = int(claims["sub"])
        user = get_active_user(user_id)
        if int(claims.get("sv", -1)) != int(user["session_version"]):
            cache.revoke_user_refresh_tokens(user_id)
            raise AuthenticationError("Session is no longer valid. Sign in again.")

        key = f"refresh:{claims['jti']}"
        expected = f"{claims['sub']}:{claims.get('family', '')}"
        if not cache.consume_if_equals(key, expected):
            family = str(claims.get("family") or "")
            if family:
                cls._revoke_family(family)
            raise AuthenticationError("Refresh token has already been used or revoked.")
        cache.unregister_refresh_token(
            user_id, str(claims["jti"]), str(claims.get("family") or "")
        )
        return cls.issue_pair(user, family=str(claims.get("family") or "")), user

    @classmethod
    def revoke(cls, access_token: str | None, refresh_token: str | None) -> None:
        if access_token:
            try:
                claims = cls.decode(access_token, "access")
                ttl = max(1, int(float(claims["exp"]) - time.time()))
                cache.client().setex(f"blacklist:{claims['jti']}", ttl, "1")
            except ApiError:
                pass
        if refresh_token:
            try:
                claims = cls.decode(refresh_token, "refresh")
                cache.client().delete(f"refresh:{claims['jti']}")
                cache.unregister_refresh_token(
                    int(claims["sub"]),
                    str(claims["jti"]),
                    str(claims.get("family") or ""),
                )
            except ApiError:
                pass


class OtpService:
    @staticmethod
    def normalize_contact(contact: str) -> tuple[str, str]:
        value = contact.strip().lower()
        if "@" in value:
            from validators import email

            return "email", email(value) or ""
        from validators import phone

        return "phone", phone(value) or ""

    @staticmethod
    def _key(purpose: str, contact: str) -> str:
        return f"otp:{purpose}:{cache.fingerprint(contact)}"

    @staticmethod
    def _digest(code: str, contact: str, purpose: str) -> str:
        return hmac.new(
            config.otp_hmac_secret.encode("utf-8"),
            f"{purpose}:{contact}:{code}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def request(cls, contact: str, purpose: str, *, ip: str = "unknown") -> dict[str, Any]:
        kind, normalized = cls.normalize_contact(contact)
        for limiter in (
            f"otp-limit:contact:{cache.fingerprint(normalized)}",
            f"otp-limit:ip:{cache.fingerprint(ip)}",
        ):
            allowed, remaining, retry_after = cache.rate_limit(
                limiter, config.otp_request_limit, config.otp_request_window_seconds
            )
            if not allowed:
                raise ApiError(
                    "rate_limited",
                    "Too many OTP requests. Try again later.",
                    429,
                    {
                        "remaining": remaining,
                        "window_seconds": config.otp_request_window_seconds,
                        "retry_after_seconds": retry_after,
                    },
                )

        cooldown_key = f"otp-cooldown:{purpose}:{cache.fingerprint(normalized)}"
        if not cache.set_once(
            cooldown_key, "1", config.otp_resend_cooldown_seconds
        ):
            retry_after = cache.ttl(cooldown_key) or config.otp_resend_cooldown_seconds
            raise ApiError(
                "otp_cooldown",
                "A verification code was sent recently. Wait before requesting another one.",
                429,
                {"retry_after_seconds": retry_after},
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        key = cls._key(purpose, normalized)
        payload = {
            "digest": cls._digest(code, normalized, purpose),
            "attempts": 0,
            "kind": kind,
            "contact": normalized,
        }
        cache.set_json(key, payload, config.otp_ttl_seconds)

        delivery_configured = (
            kind == "email" and config.otp_email_enabled
        ) or (kind == "phone" and bool(config.otp_sms_webhook_url))
        if delivery_configured:
            try:
                delivery_result = deliver_otp(
                    channel=kind,
                    destination=normalized,
                    code=code,
                    ttl_seconds=config.otp_ttl_seconds,
                    purpose=purpose,
                )
            except NotificationDeliveryError as exc:
                cache.delete(key, cooldown_key)
                logger.exception("OTP delivery failed purpose=%s channel=%s diagnostic=%s", purpose, kind, exc.diagnostic)
                details = {"channel": kind}
                if kind == "email":
                    details["hint"] = (
                        "Mailpit is not ready. Check the mailpit container."
                        if config.email_delivery_mode == "mailpit_api"
                        else "Real SMTP delivery is not ready. Check EMAIL_HOST_USER, the app password, TLS/SSL and SMTP connectivity."
                    )
                    if (
                        config.email_delivery_mode == "mailpit_api"
                        and config.public_mailpit_url
                    ):
                        details["mailbox_url"] = config.public_mailpit_url
                raise ApiError(
                    "otp_delivery_failed",
                    "The verification code could not be delivered.",
                    503,
                    details,
                ) from exc
        elif config.otp_debug_return_code:
            logger.warning(
                "LOCAL OTP purpose=%s contact=%s code=%s", purpose, mask_contact(normalized), code
            )
        else:
            cache.delete(key, cooldown_key)
            raise ApiError(
                "otp_delivery_unavailable",
                "OTP delivery is not configured for this contact channel.",
                503,
            )

        result: dict[str, Any] = {
            "destination": mask_contact(normalized),
            "channel": kind,
            "expires_in": config.otp_ttl_seconds,
            "resend_after": config.otp_resend_cooldown_seconds,
        }
        if delivery_configured:
            result["delivery_provider"] = delivery_result.get("provider")
            if delivery_result.get("message_id"):
                result["delivery_message_id"] = delivery_result["message_id"]
            if (
                kind == "email"
                and config.email_delivery_mode == "mailpit_api"
                and config.public_mailpit_url
            ):
                result["mailbox_url"] = config.public_mailpit_url
        if config.otp_debug_return_code:
            result["debug_code"] = code
        return result

    @classmethod
    def verify(cls, contact: str, code: str, purpose: str, *, consume: bool = True) -> str:
        _, normalized = cls.normalize_contact(contact)
        normalized_code = code.strip()
        if len(normalized_code) != 6 or not normalized_code.isascii() or not normalized_code.isdigit():
            raise ApiError("otp_invalid", "OTP must be exactly six digits.", 400)
        key = cls._key(purpose, normalized)
        actual = cls._digest(normalized_code, normalized, purpose)
        if not consume:
            payload = cache.get_json(key)
            if not payload:
                raise ApiError("otp_expired", "OTP is missing or expired.", 400)
            if not hmac.compare_digest(str(payload.get("digest", "")), actual):
                raise ApiError("otp_invalid", "OTP is incorrect.", 400)
            return normalized
        outcome = cache.verify_otp_digest(key, actual, config.otp_max_attempts)
        if outcome == "missing":
            raise ApiError("otp_expired", "OTP is missing or expired.", 400)
        if outcome == "locked":
            raise ApiError("otp_locked", "Too many incorrect OTP attempts.", 429)
        if outcome == "invalid":
            raise ApiError("otp_invalid", "OTP is incorrect.", 400)
        if outcome != "ok":
            raise ApiError("otp_verification_failed", "OTP could not be verified.", 503)
        return normalized


def mask_contact(contact: str) -> str:
    if "@" in contact:
        local, domain = contact.split("@", 1)
        visible = local[:2] if len(local) >= 2 else local[:1]
        return f"{visible}***@{domain}"
    if len(contact) <= 6:
        return "***"
    return f"{contact[:3]}***{contact[-3:]}"


def get_active_user(user_id: int) -> dict[str, Any]:
    row = database.fetch_one(
        """
        SELECT id,role,first_name,last_name,email::text AS email,phone,
               is_active,session_version
        FROM users WHERE id=%s
        """,
        (user_id,),
    )
    if not row or not row["is_active"]:
        raise AuthenticationError("Account is inactive or no longer exists.")
    return row


def authenticate_request(request: HttpRequest) -> Principal:
    header = request.headers.get("Authorization", "")
    scheme, separator, token = header.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError()
    claims = TokenService.decode(token.strip(), "access")
    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Token subject is invalid.") from exc
    user = get_active_user(user_id)
    if user["role"] != claims.get("role"):
        raise AuthenticationError("Account role changed. Sign in again.")
    if int(user["session_version"]) != int(claims.get("sv", -1)):
        raise AuthenticationError("Session is no longer valid. Sign in again.")
    principal = Principal(
        id=user["id"],
        role=user["role"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        phone=user["phone"],
        session_version=int(user["session_version"]),
    )
    request.principal = principal  # type: ignore[attr-defined]
    request.access_token = token.strip()  # type: ignore[attr-defined]
    return principal


def _safe_ip(value: str | None) -> str:
    candidate = (value or "").strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return "unknown"


def client_ip(request: HttpRequest) -> str:
    if config.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parsed = _safe_ip(forwarded.split(",", 1)[0])
            if parsed != "unknown":
                return parsed
    return _safe_ip(request.META.get("REMOTE_ADDR"))


def endpoint(
    methods: set[str],
    *,
    auth: bool = True,
    roles: set[str] | None = None,
    rate_limit: tuple[int, int] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, HttpResponse]]:
    """JSON endpoint wrapper with auth, RBAC, throttling and safe errors."""
    normalized_methods = {method.upper() for method in methods}

    def decorator(view: Callable[P, R]) -> Callable[P, HttpResponse]:
        @csrf_exempt
        @functools.wraps(view)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            request_id = getattr(request, "request_id", None)
            try:
                if request.method == "OPTIONS":
                    return HttpResponse(status=204)
                if request.method.upper() not in normalized_methods:
                    response = error(
                        "method_not_allowed",
                        f"Allowed methods: {', '.join(sorted(normalized_methods))}",
                        status=405,
                        request_id=request_id,
                    )
                    response["Allow"] = ", ".join(sorted(normalized_methods))
                    return response
                principal = authenticate_request(request) if auth else None
                if roles and (not principal or principal.role not in roles):
                    raise PermissionDenied()
                if rate_limit:
                    limit, window = rate_limit
                    identity = str(principal.id) if principal else client_ip(request)
                    allowed, remaining, retry_after = cache.rate_limit(
                        f"api-limit:{view.__name__}:{cache.fingerprint(identity)}",
                        limit,
                        window,
                    )
                    if not allowed:
                        raise ApiError(
                            "rate_limited",
                            "Too many requests.",
                            429,
                            {
                                "remaining": remaining,
                                "window_seconds": window,
                                "retry_after_seconds": retry_after,
                            },
                        )
                return view(request, *args, **kwargs)
            except ApiError as exc:
                response = error(
                    exc.code,
                    exc.message,
                    status=exc.status,
                    details=exc.details,
                    request_id=request_id,
                )
                if exc.status == 401:
                    response["WWW-Authenticate"] = "Bearer"
                if exc.status == 429:
                    retry_after = 60
                    if isinstance(exc.details, dict):
                        retry_after = int(
                            exc.details.get("retry_after_seconds")
                            or exc.details.get("window_seconds")
                            or retry_after
                        )
                    response["Retry-After"] = str(max(1, retry_after))
                return response
            except PsycopgError as exc:
                mapped = map_database_error(exc)
                return error(
                    mapped.code,
                    mapped.message,
                    status=mapped.status,
                    details=mapped.details,
                    request_id=request_id,
                )
            except redis.RedisError:
                logger.exception("Redis failure request_id=%s", request_id)
                return error(
                    "cache_unavailable",
                    "Authentication/cache service is temporarily unavailable.",
                    status=503,
                    request_id=request_id,
                )
            except Exception:
                logger.exception("Unhandled API error request_id=%s", request_id)
                return error(
                    "internal_error",
                    "An unexpected server error occurred.",
                    status=500,
                    request_id=request_id,
                )

        return wrapped  # type: ignore[return-value]

    return decorator
