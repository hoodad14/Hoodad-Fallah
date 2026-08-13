"""Typed environment configuration with fail-fast production checks."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from env_loader import load_env

load_env()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value")


def _int(name: str, default: int, minimum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(x.strip() for x in os.getenv(name, default).split(",") if x.strip())


_LOCAL_JWT_SECRET = "unsafe-local-jwt-secret-change-me"
_ELASTICSEARCH_INDEX_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,199}$")


@dataclass(frozen=True, slots=True)
class Config:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://arenapass:arenapass@127.0.0.1:5432/arenapass",
    )
    db_pool_min: int = _int("DB_POOL_MIN", 1, 0)
    db_pool_max: int = _int("DB_POOL_MAX", 10, 1)
    db_connect_timeout: int = _int("DB_CONNECT_TIMEOUT", 5, 1)
    db_statement_timeout_ms: int = _int("DB_STATEMENT_TIMEOUT_MS", 15000, 1000)
    db_lock_timeout_ms: int = _int("DB_LOCK_TIMEOUT_MS", 5000, 100)
    db_idle_transaction_timeout_ms: int = _int(
        "DB_IDLE_TRANSACTION_TIMEOUT_MS", 30000, 1000
    )

    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    redis_required: bool = _bool("REDIS_REQUIRED", True)

    
    
    elasticsearch_enabled: bool = _bool("ELASTICSEARCH_ENABLED", False)
    elasticsearch_url: str = os.getenv(
        "ELASTICSEARCH_URL", "http://127.0.0.1:9200"
    ).rstrip("/")
    elasticsearch_index: str = os.getenv(
        "ELASTICSEARCH_INDEX", "arenapass_tickets"
    ).strip()
    elasticsearch_timeout_seconds: int = _int(
        "ELASTICSEARCH_TIMEOUT_SECONDS", 8, 1
    )
    elasticsearch_fallback_to_sql: bool = _bool(
        "ELASTICSEARCH_FALLBACK_TO_SQL", True
    )
    elasticsearch_sync_on_startup: bool = _bool(
        "ELASTICSEARCH_SYNC_ON_STARTUP", True
    )
    elasticsearch_sync_batch_size: int = _int(
        "ELASTICSEARCH_SYNC_BATCH_SIZE", 500, 1
    )
    elasticsearch_outbox_batch_size: int = _int(
        "ELASTICSEARCH_OUTBOX_BATCH_SIZE", 100, 1
    )
    elasticsearch_full_sync_seconds: int = _int(
        "ELASTICSEARCH_FULL_SYNC_SECONDS", 3600, 60
    )
    elasticsearch_outbox_retention_days: int = _int(
        "ELASTICSEARCH_OUTBOX_RETENTION_DAYS", 7, 1
    )
    elasticsearch_api_key: str = os.getenv("ELASTICSEARCH_API_KEY", "").strip()
    elasticsearch_username: str = os.getenv(
        "ELASTICSEARCH_USERNAME", ""
    ).strip()
    elasticsearch_password: str = os.getenv(
        "ELASTICSEARCH_PASSWORD", ""
    ).strip()

    jwt_secret: str = os.getenv("JWT_SECRET", _LOCAL_JWT_SECRET)
    jwt_issuer: str = os.getenv("JWT_ISSUER", "arenapass-api")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "arenapass-client")
    access_token_minutes: int = _int("ACCESS_TOKEN_MINUTES", 15, 1)
    refresh_token_days: int = _int("REFRESH_TOKEN_DAYS", 14, 1)

    otp_hmac_secret: str = os.getenv(
        "OTP_HMAC_SECRET", os.getenv("JWT_SECRET", _LOCAL_JWT_SECRET)
    )
    otp_ttl_seconds: int = _int("OTP_TTL_SECONDS", 300, 60)
    otp_max_attempts: int = _int("OTP_MAX_ATTEMPTS", 5, 1)
    otp_request_window_seconds: int = _int("OTP_REQUEST_WINDOW_SECONDS", 600, 60)
    otp_request_limit: int = _int("OTP_REQUEST_LIMIT", 5, 1)
    otp_resend_cooldown_seconds: int = _int("OTP_RESEND_COOLDOWN_SECONDS", 45, 1)
    signup_ttl_seconds: int = _int("SIGNUP_TTL_SECONDS", 600, 120)
    auth_password_max_attempts: int = _int("AUTH_PASSWORD_MAX_ATTEMPTS", 5, 1)
    auth_password_window_seconds: int = _int("AUTH_PASSWORD_WINDOW_SECONDS", 900, 60)
    auth_password_lock_seconds: int = _int("AUTH_PASSWORD_LOCK_SECONDS", 900, 60)
    otp_debug_return_code: bool = _bool("OTP_DEBUG_RETURN_CODE", False)
    otp_email_enabled: bool = _bool("OTP_EMAIL_ENABLED", False)
    otp_email_required: bool = _bool("OTP_EMAIL_REQUIRED", False)
    email_delivery_mode: str = os.getenv("EMAIL_DELIVERY_MODE", "smtp").strip().lower()
    email_delivery_retries: int = _int("EMAIL_DELIVERY_RETRIES", 3, 1)
    email_delivery_retry_delay_ms: int = _int("EMAIL_DELIVERY_RETRY_DELAY_MS", 350, 0)
    email_healthcheck_cache_seconds: int = _int(
        "EMAIL_HEALTHCHECK_CACHE_SECONDS", 300, 5
    )
    mailpit_api_url: str = os.getenv("MAILPIT_API_URL", "").strip().rstrip("/")
    mailpit_verify_delivery: bool = _bool("MAILPIT_VERIFY_DELIVERY", True)
    public_mailpit_url: str = os.getenv("PUBLIC_MAILPIT_URL", "").strip()
    otp_sms_webhook_url: str = os.getenv("OTP_SMS_WEBHOOK_URL", "").strip()
    otp_sms_bearer_token: str = os.getenv("OTP_SMS_BEARER_TOKEN", "").strip()
    notification_timeout_seconds: int = _int("NOTIFICATION_TIMEOUT_SECONDS", 8, 1)

    cache_default_seconds: int = _int("CACHE_DEFAULT_SECONDS", 120, 1)
    cache_ticket_seconds: int = _int("CACHE_TICKET_SECONDS", 60, 1)
    profile_cache_seconds: int = _int("PROFILE_CACHE_SECONDS", 300, 1)

    allowed_origins: tuple[str, ...] = _csv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://127.0.0.1:8080,http://localhost:8081,http://127.0.0.1:8081",
    )
    allow_all_origins: bool = _bool("CORS_ALLOW_ALL", False)
    secure_cookies: bool = _bool("SECURE_COOKIES", False)
    trust_proxy_headers: bool = _bool("TRUST_PROXY_HEADERS", False)

    allow_local_wallet_top_up: bool = _bool("ALLOW_LOCAL_WALLET_TOP_UP", True)
    worker_interval_seconds: int = _int("WORKER_INTERVAL_SECONDS", 30, 5)
    payment_reminder_enabled: bool = _bool("PAYMENT_REMINDER_ENABLED", False)
    payment_reminder_before_seconds: int = _int(
        "PAYMENT_REMINDER_BEFORE_SECONDS", 180, 30
    )


config = Config()
if config.db_pool_min > config.db_pool_max:
    raise RuntimeError("DB_POOL_MIN cannot exceed DB_POOL_MAX")
if config.email_delivery_mode not in {"smtp", "mailpit_api"}:
    raise RuntimeError("EMAIL_DELIVERY_MODE must be smtp or mailpit_api")
if config.email_delivery_mode == "mailpit_api" and not config.mailpit_api_url:
    raise RuntimeError("MAILPIT_API_URL is required when EMAIL_DELIVERY_MODE=mailpit_api")


def validate_production_config(debug: bool) -> None:
    """Reject settings that are acceptable only for local demonstration."""
    if debug:
        return

    django_secret = os.getenv("DJANGO_SECRET_KEY", "")
    weak = {
        "JWT_SECRET": config.jwt_secret.startswith("unsafe-") or len(config.jwt_secret) < 32,
        "OTP_HMAC_SECRET": config.otp_hmac_secret.startswith("unsafe-")
        or len(config.otp_hmac_secret) < 32,
        "DJANGO_SECRET_KEY": django_secret.startswith("unsafe-") or len(django_secret) < 32,
        "OTP_DEBUG_RETURN_CODE": config.otp_debug_return_code,
        "CORS_ALLOW_ALL": config.allow_all_origins,
        "ALLOW_LOCAL_WALLET_TOP_UP": config.allow_local_wallet_top_up,
    }
    if config.jwt_secret == config.otp_hmac_secret:
        weak["OTP_HMAC_SECRET_MUST_DIFFER_FROM_JWT_SECRET"] = True

    email_backend = os.getenv(
        "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
    )
    has_sms = bool(config.otp_sms_webhook_url)
    weak["MAILPIT_API_LOCAL_ONLY"] = (
        config.otp_email_enabled and config.email_delivery_mode == "mailpit_api"
    )
    weak["OTP_DELIVERY_PROVIDER"] = not (config.otp_email_enabled or has_sms)
    weak["CONSOLE_EMAIL_BACKEND"] = (
        config.otp_email_enabled
        and config.email_delivery_mode == "smtp"
        and "console" in email_backend.lower()
    )
    email_host = os.getenv("EMAIL_HOST", "").strip()
    email_host_user = os.getenv("EMAIL_HOST_USER", "").strip()
    email_host_password = os.getenv("EMAIL_HOST_PASSWORD", "").strip()
    email_use_tls = _bool("EMAIL_USE_TLS", False)
    email_use_ssl = _bool("EMAIL_USE_SSL", False)
    weak["SMTP_HOST"] = (
        config.otp_email_enabled
        and config.email_delivery_mode == "smtp"
        and not email_host
    )
    weak["SMTP_TLS_SSL_CONFLICT"] = email_use_tls and email_use_ssl
    weak["SMTP_TRANSPORT_SECURITY"] = (
        config.otp_email_enabled
        and config.email_delivery_mode == "smtp"
        and not (email_use_tls or email_use_ssl)
    )
    using_gmail = email_host.lower() == "smtp.gmail.com"
    weak["GMAIL_SMTP_USERNAME"] = (
        config.otp_email_enabled
        and config.email_delivery_mode == "smtp"
        and using_gmail
        and (
            not email_host_user
            or email_host_user.lower() in {"change_me@gmail.com", "your_gmail@gmail.com"}
        )
    )
    weak["GMAIL_APP_PASSWORD"] = (
        config.otp_email_enabled
        and config.email_delivery_mode == "smtp"
        and using_gmail
        and (
            not email_host_password
            or email_host_password.lower()
            in {"change_me_app_password", "your_app_password"}
        )
    )
    weak["OTP_SMS_WEBHOOK_HTTPS"] = has_sms and urlparse(
        config.otp_sms_webhook_url
    ).scheme.lower() != "https"
    elasticsearch_url = urlparse(config.elasticsearch_url)
    weak["ELASTICSEARCH_URL"] = config.elasticsearch_enabled and (
        elasticsearch_url.scheme.lower() not in {"http", "https"}
        or not elasticsearch_url.hostname
    )
    weak["ELASTICSEARCH_INDEX"] = (
        config.elasticsearch_enabled
        and not _ELASTICSEARCH_INDEX_RE.fullmatch(config.elasticsearch_index)
    )
    weak["ELASTICSEARCH_BASIC_AUTH"] = bool(
        config.elasticsearch_username
    ) != bool(config.elasticsearch_password)
    weak["ELASTICSEARCH_AUTH_CONFLICT"] = bool(
        config.elasticsearch_api_key
        and (config.elasticsearch_username or config.elasticsearch_password)
    )
    has_elasticsearch_auth = bool(
        config.elasticsearch_api_key
        or config.elasticsearch_username
        or config.elasticsearch_password
    )
    weak["ELASTICSEARCH_AUTH_REQUIRES_HTTPS"] = bool(
        config.elasticsearch_enabled
        and has_elasticsearch_auth
        and elasticsearch_url.scheme.lower() != "https"
    )

    broken = [name for name, bad in weak.items() if bad]
    if broken:
        raise RuntimeError("Unsafe production configuration: " + ", ".join(broken))
