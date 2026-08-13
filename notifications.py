"""Reliable email/SMS delivery for authentication workflows.

The selected provider is controlled by environment variables. Gmail and other
real providers use Django SMTP; Mailpit remains available as a local fallback.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid
from email.utils import parseaddr
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from config import config

logger = logging.getLogger(__name__)

_transport_status_lock = threading.Lock()
_transport_status_cached_at = 0.0
_transport_status_cached_value: tuple[bool, str] | None = None


class NotificationDeliveryError(RuntimeError):
    """A provider rejected or could not persist a notification."""

    def __init__(self, message: str, *, diagnostic: str | None = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic or message


def _mailpit_url(path: str) -> str:
    if not config.mailpit_api_url:
        raise NotificationDeliveryError("Mailpit API URL is not configured.")
    return f"{config.mailpit_api_url}/{path.lstrip('/')}"


def _http_request(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int | None = None,
) -> tuple[int, bytes]:
    body = None
    headers = {"Accept": "application/json", "User-Agent": "ArenaPass/OTP"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(
            request, timeout=timeout or config.notification_timeout_seconds
        ) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:800]
        raise NotificationDeliveryError(
            "Mailpit HTTP API rejected the request.",
            diagnostic=f"HTTP {exc.code}: {detail}",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise NotificationDeliveryError(
            "Mailpit HTTP API is unreachable.",
            diagnostic=f"{type(exc).__name__}: {exc}",
        ) from exc


def _smtp_configuration_error() -> str | None:
    backend = str(settings.EMAIL_BACKEND or "")
    if "console" in backend.lower() or "dummy" in backend.lower():
        return "The configured email backend does not deliver to SMTP."
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        return "EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled."
    host = str(settings.EMAIL_HOST or "").strip().lower()
    if not host:
        return "EMAIL_HOST is not configured."
    if not 1 <= int(settings.EMAIL_PORT) <= 65535:
        return "EMAIL_PORT is invalid."

    if host == "smtp.gmail.com":
        username = str(settings.EMAIL_HOST_USER or "").strip()
        password = str(settings.EMAIL_HOST_PASSWORD or "").strip()
        placeholder_values = {
            "change_me@gmail.com",
            "your_gmail@gmail.com",
            "change_me_app_password",
            "your_app_password",
        }
        if not username or username.lower() in placeholder_values:
            return "Gmail SMTP username is missing. Set EMAIL_HOST_USER."
        if not password or password.lower() in placeholder_values:
            return "Gmail app password is missing. Set EMAIL_HOST_PASSWORD."
        if int(settings.EMAIL_PORT) == 587 and not settings.EMAIL_USE_TLS:
            return "Gmail port 587 requires EMAIL_USE_TLS=true."
        if int(settings.EMAIL_PORT) == 465 and not settings.EMAIL_USE_SSL:
            return "Gmail port 465 requires EMAIL_USE_SSL=true."
        if int(settings.EMAIL_PORT) not in {465, 587}:
            return "Gmail SMTP must use port 587 (TLS) or 465 (SSL)."
    return None


def _probe_email_transport() -> tuple[bool, str]:
    if not config.otp_email_enabled:
        return False, "OTP email delivery is disabled."

    if config.email_delivery_mode == "mailpit_api":
        try:
            status, _ = _http_request("GET", _mailpit_url("api/v1/info"), timeout=4)
            if status == 200:
                return True, "Mailpit HTTP API delivery is ready."
            return False, f"Mailpit readiness returned HTTP {status}."
        except NotificationDeliveryError as exc:
            return False, exc.diagnostic

    configuration_error = _smtp_configuration_error()
    if configuration_error:
        return False, configuration_error
    connection = get_connection(fail_silently=False)
    try:
        opened = connection.open()
        if opened is False and getattr(connection, "connection", None) is None:
            return False, "The email backend did not open an SMTP connection."
        return True, "SMTP transport is ready."
    except Exception as exc:  # SMTP/backend-specific exception types vary
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        try:
            connection.close()
        except Exception:
            pass


def email_transport_status(*, force: bool = False) -> tuple[bool, str]:
    """Check email delivery readiness without repeatedly authenticating to SMTP.

    Docker calls the readiness endpoint frequently. Authenticating to Gmail on
    every health check can create unnecessary latency and provider throttling,
    so successful/failed probes are cached for a short configurable interval.
    Startup code can pass ``force=True`` when it explicitly needs a fresh probe.
    """

    global _transport_status_cached_at, _transport_status_cached_value
    now = time.monotonic()
    with _transport_status_lock:
        if (
            not force
            and _transport_status_cached_value is not None
            and now - _transport_status_cached_at
            < config.email_healthcheck_cache_seconds
        ):
            return _transport_status_cached_value

        result = _probe_email_transport()
        _transport_status_cached_at = time.monotonic()
        _transport_status_cached_value = result
        return result


def _post_sms(payload: dict[str, Any]) -> None:
    if not config.otp_sms_webhook_url:
        raise NotificationDeliveryError("SMS webhook is not configured.")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if config.otp_sms_bearer_token:
        headers["Authorization"] = f"Bearer {config.otp_sms_bearer_token}"
    request = urllib.request.Request(
        config.otp_sms_webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=config.notification_timeout_seconds
        ) as response:
            if not 200 <= response.status < 300:
                raise NotificationDeliveryError(
                    f"SMS webhook returned HTTP {response.status}."
                )
    except (urllib.error.URLError, TimeoutError) as exc:
        raise NotificationDeliveryError("SMS webhook request failed.") from exc


def _purpose_title(purpose: str) -> str:
    if purpose == "login":
        return "ورود به حساب MahTicket"
    if purpose.startswith("signup:"):
        return "تأیید ثبت‌نام MahTicket"
    if purpose.startswith("password_change:"):
        return "تأیید تغییر رمز عبور MahTicket"
    if purpose.startswith("contact_change:"):
        return "تأیید راه ارتباطی MahTicket"
    return "کد تأیید MahTicket"


def _masked_destination(destination: str) -> str:
    if "@" in destination:
        local, domain = destination.split("@", 1)
        visible = local[:2] if len(local) > 1 else local[:1]
        return f"{visible}***@{domain}"
    return "***"


def _send_via_mailpit_api(
    *, subject: str, text: str, html: str, destination: str, purpose: str
) -> dict[str, str]:
    from_name, from_address = parseaddr(str(settings.DEFAULT_FROM_EMAIL))
    from_address = from_address or "noreply@arenapass.local"
    delivery_id = uuid.uuid4().hex
    payload = {
        "From": {"Email": from_address, "Name": from_name or "MahTicket"},
        "To": [{"Email": destination}],
        "Subject": subject,
        "Text": text,
        "HTML": html,
        "Headers": {
            "X-ArenaPass-Delivery-ID": delivery_id,
            "Auto-Submitted": "auto-generated",
        },
        "Tags": ["arenapass", "otp", purpose.split(":", 1)[0]],
    }
    last_error: NotificationDeliveryError | None = None
    for attempt in range(1, max(1, config.email_delivery_retries) + 1):
        try:
            status, body = _http_request(
                "POST", _mailpit_url("api/v1/send"), payload=payload
            )
            if status != 200:
                raise NotificationDeliveryError(
                    "Mailpit did not accept the email.",
                    diagnostic=f"Unexpected HTTP status {status}",
                )
            try:
                parsed = json.loads(body.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise NotificationDeliveryError(
                    "Mailpit returned an invalid JSON response.",
                    diagnostic=f"{type(exc).__name__}: {exc}",
                ) from exc
            message_id = str(parsed.get("ID") or "").strip()
            if not message_id:
                raise NotificationDeliveryError(
                    "Mailpit accepted the request but returned no message ID."
                )
            if config.mailpit_verify_delivery:
                encoded_id = urllib.parse.quote(message_id, safe="")
                persisted = False
                verification_error: NotificationDeliveryError | None = None
                for verify_attempt in range(1, 5):
                    try:
                        verify_status, _ = _http_request(
                            "GET", _mailpit_url(f"api/v1/message/{encoded_id}")
                        )
                        if verify_status == 200:
                            persisted = True
                            break
                        verification_error = NotificationDeliveryError(
                            "Mailpit did not persist the email.",
                            diagnostic=f"Message verification returned HTTP {verify_status}",
                        )
                    except NotificationDeliveryError as exc:
                        verification_error = exc
                    if verify_attempt < 4:
                        time.sleep(0.1 * verify_attempt)
                if not persisted:
                    raise NotificationDeliveryError(
                        "Mailpit accepted the email but it could not be verified in storage.",
                        diagnostic=(verification_error.diagnostic if verification_error else "message verification failed"),
                    ) from verification_error
            logger.info(
                "OTP email persisted in Mailpit destination=%s message_id=%s delivery_id=%s",
                _masked_destination(destination),
                message_id,
                delivery_id,
            )
            return {
                "provider": "mailpit_api",
                "message_id": message_id,
                "delivery_id": delivery_id,
            }
        except NotificationDeliveryError as exc:
            last_error = exc
            logger.warning(
                "Mailpit email attempt failed destination=%s attempt=%s/%s diagnostic=%s",
                _masked_destination(destination),
                attempt,
                config.email_delivery_retries,
                exc.diagnostic,
            )
            if attempt < config.email_delivery_retries:
                time.sleep((config.email_delivery_retry_delay_ms / 1000) * attempt)
    assert last_error is not None
    raise NotificationDeliveryError(
        "OTP email delivery failed.", diagnostic=last_error.diagnostic
    ) from last_error


def _send_via_smtp(
    *, subject: str, text: str, html: str, destination: str
) -> dict[str, str]:
    last_error: Exception | None = None
    delivery_id = uuid.uuid4().hex
    attempts = max(1, config.email_delivery_retries)
    for attempt in range(1, attempts + 1):
        connection = get_connection(fail_silently=False)
        try:
            message = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destination],
                headers={
                    "X-ArenaPass-Delivery-ID": delivery_id,
                    "Auto-Submitted": "auto-generated",
                },
                connection=connection,
            )
            message.attach_alternative(html, "text/html")
            connection.open()
            sent = connection.send_messages([message])
            if sent != 1:
                raise RuntimeError(f"email backend accepted {sent!r} messages")
            logger.info(
                "Email accepted by SMTP destination=%s host=%s port=%s attempt=%s delivery_id=%s",
                _masked_destination(destination),
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                attempt,
                delivery_id,
            )
            return {"provider": "smtp", "delivery_id": delivery_id}
        except Exception as exc:
            last_error = exc
            logger.warning(
                "SMTP delivery failed destination=%s host=%s port=%s attempt=%s/%s error=%s: %s",
                _masked_destination(destination),
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                attempt,
                attempts,
                type(exc).__name__,
                exc,
            )
            if attempt < attempts:
                time.sleep((config.email_delivery_retry_delay_ms / 1000) * attempt)
        finally:
            try:
                connection.close()
            except Exception:
                pass
    assert last_error is not None
    raise NotificationDeliveryError(
        "OTP email delivery failed.",
        diagnostic=f"{type(last_error).__name__}: {last_error}",
    ) from last_error


def _send_email_message(
    *, subject: str, text: str, html: str, destination: str, purpose: str
) -> dict[str, str]:
    if config.email_delivery_mode == "mailpit_api":
        return _send_via_mailpit_api(
            subject=subject,
            text=text,
            html=html,
            destination=destination,
            purpose=purpose,
        )
    return _send_via_smtp(
        subject=subject, text=text, html=html, destination=destination
    )


def deliver_test_email(destination: str) -> dict[str, str]:
    """Send a non-OTP message for validating the configured real mailbox."""
    text = (
        "MahTicket email delivery is configured correctly.\n\n"
        "This message was sent by the SMTP smoke test and contains no login code."
    )
    html = """
    <div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;max-width:520px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:14px">
      <h2 style="margin-top:0">تست ایمیل MahTicket موفق بود</h2>
      <p>این پیام از سرویس SMTP واقعی پروژه ارسال شده است.</p>
      <p style="color:#6b7280;font-size:13px">این ایمیل صرفاً برای تست تنظیمات است و کد ورود ندارد.</p>
    </div>
    """
    return _send_email_message(
        subject="MahTicket real email test",
        text=text,
        html=html,
        destination=destination,
        purpose="smtp_test",
    )


def deliver_otp(
    *,
    channel: str,
    destination: str,
    code: str,
    ttl_seconds: int,
    purpose: str = "otp",
) -> dict[str, str]:
    minutes = max(1, ttl_seconds // 60)
    title = _purpose_title(purpose)
    message = (
        f"{title}\n\n"
        f"کد یکبار مصرف شما: {code}\n"
        f"اعتبار کد: {minutes} دقیقه\n\n"
        "این کد را در اختیار هیچ‌کس قرار ندهید. اگر این درخواست را شما ثبت نکرده‌اید، "
        "این پیام را نادیده بگیرید."
    )
    html_message = f"""
    <div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;max-width:520px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:14px">
      <h2 style="margin-top:0">{title}</h2>
      <p>کد یکبار مصرف شما:</p>
      <div dir="ltr" style="font-size:32px;font-weight:800;letter-spacing:8px;text-align:center;background:#f3f4f6;border-radius:12px;padding:18px">{code}</div>
      <p>این کد تا <b>{minutes} دقیقه</b> معتبر است.</p>
      <p style="color:#6b7280;font-size:13px">کد را در اختیار هیچ‌کس قرار ندهید. اگر این درخواست را شما ثبت نکرده‌اید، پیام را نادیده بگیرید.</p>
    </div>
    """
    if channel == "email":
        if not config.otp_email_enabled:
            raise NotificationDeliveryError("OTP email delivery is not enabled.")
        return _send_email_message(
            subject=title,
            text=message,
            html=html_message,
            destination=destination,
            purpose=purpose,
        )
    if channel == "phone":
        _post_sms(
            {
                "to": destination,
                "message": message,
                "purpose": purpose,
                "expires_in": ttl_seconds,
            }
        )
        return {"provider": "sms_webhook"}
    raise NotificationDeliveryError(f"Unsupported notification channel: {channel}")


def deliver_payment_reminder(
    *, channel: str, destination: str, reservation_id: int, expires_in_seconds: int
) -> None:
    minutes = max(1, expires_in_seconds // 60)
    message = (
        f"MahTicket reservation {reservation_id} expires in about {minutes} minute(s). "
        "Complete payment before the hold is released."
    )
    if channel == "email":
        _send_email_message(
            subject="MahTicket payment reminder",
            text=message,
            html=f"<p>{message}</p>",
            destination=destination,
            purpose="payment_reminder",
        )
        return
    if channel == "phone":
        _post_sms(
            {
                "to": destination,
                "message": message,
                "purpose": "payment_reminder",
                "reservation_id": reservation_id,
                "expires_in": expires_in_seconds,
            }
        )
        return
    raise NotificationDeliveryError(f"Unsupported notification channel: {channel}")
