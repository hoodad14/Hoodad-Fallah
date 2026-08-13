"""Authentication and profile use-cases implemented with raw SQL."""
from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Any

import cache
import database
from audit import record as audit
from authentication import OtpService, TokenService, mask_contact
from config import config
from exceptions import ApiError, AuthenticationError, Conflict, NotFound

USER_PUBLIC_SELECT = """
SELECT u.id,u.first_name,u.last_name,u.email::text AS email,u.phone,u.role,
       u.date_of_birth,u.profile_picture_url,u.preferred_login,u.is_active,
       u.created_at,u.updated_at,u.city_id,c.name AS city_name,p.name AS province_name,
       (u.email_verified_at IS NOT NULL) AS email_verified,
       (u.phone_verified_at IS NOT NULL) AS phone_verified,
       u.last_login_at
FROM users u
LEFT JOIN cities c ON c.id=u.city_id
LEFT JOIN provinces p ON p.id=c.province_id
"""

_REGISTRATION_ID_RE = re.compile(r"^[a-f0-9]{32}$")


def find_user_by_contact(contact: str) -> dict[str, Any] | None:
    _, normalized = OtpService.normalize_contact(contact)
    return database.fetch_one(
        USER_PUBLIC_SELECT + " WHERE lower(u.email::text)=lower(%s) OR u.phone=%s",
        (normalized, normalized),
    )


def _contact_available(email: str | None, phone: str | None) -> None:
    row = database.fetch_one(
        """
        SELECT id
        FROM users
        WHERE (%s::text IS NOT NULL AND lower(email::text)=lower(%s::text))
           OR (%s::text IS NOT NULL AND phone=%s::text)
        LIMIT 1
        """,
        (email, email, phone, phone),
    )
    if row:
        raise Conflict("An account with this email or phone already exists.")


def _hash_password(password: str) -> str:
    row = database.execute(
        "SELECT crypt(%s,gen_salt('bf',12)) AS password_hash",
        (password,),
        returning=True,
    )
    if not row or not row.get("password_hash"):
        raise ApiError("password_hash_failed", "Password could not be secured.", 503)
    return str(row["password_hash"])


def _pending_signup_key(registration_id: str) -> str:
    return f"pending-signup:{registration_id}"


def request_signup(
    *,
    first_name: str,
    last_name: str,
    email: str | None,
    phone: str | None,
    password: str,
    preferred_login: str,
    city_id: int | None,
    date_of_birth: date | None,
    ip_address: str,
) -> dict[str, Any]:
    """Validate signup data, store only a password hash, and send a contact OTP."""
    if not email and not phone:
        raise ApiError("validation_error", "At least email or phone is required.", 422)
    if preferred_login not in {"email", "phone"}:
        raise ApiError("validation_error", "preferred_login must be email or phone.", 422)
    if preferred_login == "email" and not email:
        raise ApiError("validation_error", "Email is required for preferred email login.", 422)
    if preferred_login == "phone" and not phone:
        raise ApiError("validation_error", "Phone is required for preferred phone login.", 422)

    _contact_available(email, phone)
    verification_contact = email if preferred_login == "email" else phone
    assert verification_contact is not None

    registration_id = uuid.uuid4().hex
    purpose = f"signup:{registration_id}"
    pending = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "password_hash": _hash_password(password),
        "preferred_login": preferred_login,
        "city_id": city_id,
        "date_of_birth": date_of_birth.isoformat() if date_of_birth else None,
        "verification_contact": verification_contact,
    }
    key = _pending_signup_key(registration_id)
    cache.set_json(key, pending, config.signup_ttl_seconds)
    try:
        delivery = OtpService.request(verification_contact, purpose, ip=ip_address)
    except Exception:
        cache.delete(key)
        raise
    return {
        "registration_id": registration_id,
        "destination": delivery["destination"],
        "channel": delivery["channel"],
        "expires_in": min(config.signup_ttl_seconds, int(delivery["expires_in"])),
        "resend_after": delivery.get("resend_after", config.otp_resend_cooldown_seconds),
        **({"debug_code": delivery["debug_code"]} if delivery.get("debug_code") else {}),
        **({"delivery_provider": delivery["delivery_provider"]} if delivery.get("delivery_provider") else {}),
        **({"mailbox_url": delivery["mailbox_url"]} if delivery.get("mailbox_url") else {}),
        **({"delivery_message_id": delivery["delivery_message_id"]} if delivery.get("delivery_message_id") else {}),
    }


def resend_signup_otp(
    registration_id: str,
    *,
    ip_address: str,
) -> dict[str, Any]:
    """Resend the OTP for an existing, unexpired pending registration."""
    normalized_id = registration_id.strip().lower()
    if not _REGISTRATION_ID_RE.fullmatch(normalized_id):
        raise ApiError("signup_expired", "Signup request is invalid or expired.", 400)
    pending = cache.get_json(_pending_signup_key(normalized_id))
    if not isinstance(pending, dict):
        raise ApiError("signup_expired", "Signup request is invalid or expired.", 400)
    contact = str(pending.get("verification_contact") or "")
    if not contact:
        raise ApiError("signup_expired", "Signup request is invalid or expired.", 400)
    delivery = OtpService.request(contact, f"signup:{normalized_id}", ip=ip_address)
    return {
        "registration_id": normalized_id,
        "destination": delivery["destination"],
        "channel": delivery["channel"],
        "expires_in": min(config.signup_ttl_seconds, int(delivery["expires_in"])),
        "resend_after": delivery.get("resend_after", config.otp_resend_cooldown_seconds),
        **({"debug_code": delivery["debug_code"]} if delivery.get("debug_code") else {}),
        **({"delivery_provider": delivery["delivery_provider"]} if delivery.get("delivery_provider") else {}),
        **({"mailbox_url": delivery["mailbox_url"]} if delivery.get("mailbox_url") else {}),
        **({"delivery_message_id": delivery["delivery_message_id"]} if delivery.get("delivery_message_id") else {}),
    }


def verify_signup(
    registration_id: str,
    code: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Consume a signup OTP, create the account atomically, and issue JWTs."""
    normalized_id = registration_id.strip().lower()
    if not _REGISTRATION_ID_RE.fullmatch(normalized_id):
        raise ApiError("signup_expired", "Signup request is invalid or expired.", 400)
    key = _pending_signup_key(normalized_id)
    pending = cache.get_json(key)
    if not isinstance(pending, dict):
        raise ApiError("signup_expired", "Signup request is invalid or expired.", 400)

    contact = str(pending.get("verification_contact") or "")
    OtpService.verify(contact, code, f"signup:{normalized_id}")
    email = pending.get("email") or None
    phone = pending.get("phone") or None
    preferred_login = str(pending.get("preferred_login") or "email")
    birth_raw = pending.get("date_of_birth")
    birth = date.fromisoformat(str(birth_raw)) if birth_raw else None

    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM users
            WHERE (%s::text IS NOT NULL AND lower(email::text)=lower(%s::text))
               OR (%s::text IS NOT NULL AND phone=%s::text)
            LIMIT 1
            FOR UPDATE
            """,
            (email, email, phone, phone),
        )
        if cur.fetchone():
            raise Conflict("An account with this email or phone already exists.")

        email_verified = preferred_login == "email"
        phone_verified = preferred_login == "phone"
        cur.execute(
            """
            INSERT INTO users
                (city_id,first_name,last_name,email,phone,password_hash,role,
                 date_of_birth,preferred_login,is_active,email_verified_at,
                 phone_verified_at,last_login_at)
            VALUES (%s,%s,%s,%s,%s,%s,'spectator',%s,%s,TRUE,
                    CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (
                pending.get("city_id"),
                pending.get("first_name"),
                pending.get("last_name"),
                email,
                phone,
                pending.get("password_hash"),
                birth,
                preferred_login,
                email_verified,
                phone_verified,
            ),
        )
        user_id = int(cur.fetchone()["id"])
        audit(
            conn,
            actor_user_id=user_id,
            action="user.signup.verified",
            resource_type="user",
            resource_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"verification_channel": preferred_login},
        )

    cache.delete(key)
    user = get_profile(user_id, use_cache=False)
    return user, TokenService.issue_pair(user)


def _login_lock_keys(normalized: str) -> tuple[str, str]:
    fingerprint = cache.fingerprint(normalized)
    return f"password-fail:{fingerprint}", f"password-lock:{fingerprint}"


def password_login(contact: str, password: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _, normalized = OtpService.normalize_contact(contact)
    failure_key, lock_key = _login_lock_keys(normalized)
    retry_after = cache.ttl(lock_key)
    if retry_after:
        raise ApiError(
            "login_temporarily_locked",
            "Too many failed sign-in attempts. Try again later.",
            429,
            {"retry_after_seconds": retry_after},
        )

    row = database.fetch_one(
        """
        SELECT u.id,u.first_name,u.last_name,u.email::text AS email,u.phone,u.role,
               u.date_of_birth,u.profile_picture_url,u.preferred_login,u.is_active,
               u.created_at,u.updated_at,u.city_id,c.name AS city_name,p.name AS province_name,
               (u.email_verified_at IS NOT NULL) AS email_verified,
               (u.phone_verified_at IS NOT NULL) AS phone_verified,
               u.last_login_at,
               (u.password_hash=crypt(%s,u.password_hash)) AS password_ok
        FROM users u
        LEFT JOIN cities c ON c.id=u.city_id
        LEFT JOIN provinces p ON p.id=c.province_id
        WHERE (lower(u.email::text)=lower(%s) AND u.email_verified_at IS NOT NULL)
           OR (u.phone=%s AND u.phone_verified_at IS NOT NULL)
        """,
        (password, normalized, normalized),
    )
    if not row or not row["is_active"] or not row.get("password_ok"):
        allowed, _, retry_after = cache.rate_limit(
            failure_key,
            config.auth_password_max_attempts,
            config.auth_password_window_seconds,
        )
        if not allowed:
            cache.client().setex(lock_key, config.auth_password_lock_seconds, "1")
            cache.delete(failure_key)
            raise ApiError(
                "login_temporarily_locked",
                "Too many failed sign-in attempts. Try again later.",
                429,
                {"retry_after_seconds": config.auth_password_lock_seconds},
            )
        raise AuthenticationError("Contact or password is incorrect.")

    cache.delete(failure_key, lock_key)
    login_row = database.execute(
        "UPDATE users SET last_login_at=CURRENT_TIMESTAMP WHERE id=%s RETURNING last_login_at",
        (int(row["id"]),),
        returning=True,
    )
    row.pop("password_ok", None)
    if login_row:
        row["last_login_at"] = login_row["last_login_at"]
    return row, TokenService.issue_pair(row)


def otp_login(contact: str, code: str) -> tuple[dict[str, Any], dict[str, Any]]:
    kind, _ = OtpService.normalize_contact(contact)
    normalized = OtpService.verify(contact, code, "login")
    user = find_user_by_contact(normalized)
    if not user or not user["is_active"]:
        raise AuthenticationError("Account is inactive or does not exist.")
    verified_column = "email_verified_at" if kind == "email" else "phone_verified_at"
    database.execute(
        f"""
        UPDATE users
        SET {verified_column}=COALESCE({verified_column},CURRENT_TIMESTAMP),
            last_login_at=CURRENT_TIMESTAMP
        WHERE id=%s
        """,
        (int(user["id"]),),
    )
    cache.delete(f"profile:{int(user['id'])}")
    user = get_profile(int(user["id"]), use_cache=False)
    return user, TokenService.issue_pair(user)


def request_login_otp(contact: str, ip: str) -> dict[str, Any]:
    """Send a login OTP only for an existing, active account.

    The product flow deliberately returns an explicit account-not-found error
    so the frontend remains on the request form for unknown contacts.
    """
    kind, normalized = OtpService.normalize_contact(contact)
    user = find_user_by_contact(normalized)
    if not user:
        # Preserve anti-abuse limits even though this product flow intentionally
        # reports that the account is missing.
        for limiter in (
            f"otp-limit:contact:{cache.fingerprint(normalized)}",
            f"otp-limit:ip:{cache.fingerprint(ip)}",
        ):
            allowed, _, retry_after = cache.rate_limit(
                limiter, config.otp_request_limit, config.otp_request_window_seconds
            )
            if not allowed:
                raise ApiError(
                    "rate_limited",
                    "Too many OTP requests. Try again later.",
                    429,
                    {
                        "window_seconds": config.otp_request_window_seconds,
                        "retry_after_seconds": retry_after,
                    },
                )
        raise ApiError(
            "account_not_found",
            "No account exists with this email or phone number.",
            404,
            {"contact_type": kind},
        )
    if not user["is_active"]:
        raise ApiError(
            "account_inactive",
            "This account is inactive. Contact support for assistance.",
            403,
        )
    return OtpService.request(normalized, "login", ip=ip)


def get_profile(user_id: int, *, use_cache: bool = True) -> dict[str, Any]:
    key = f"profile:{user_id}"
    if use_cache and (cached := cache.get_json(key)) is not None:
        return cached
    row = database.fetch_one(USER_PUBLIC_SELECT + " WHERE u.id=%s", (user_id,))
    if not row:
        raise NotFound("User profile not found.")
    cache.set_json(key, row, config.profile_cache_seconds)
    return row


def update_profile(
    user_id: int,
    fields: dict[str, Any],
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    allowed = {
        "first_name": "first_name",
        "last_name": "last_name",
        "city_id": "city_id",
        "date_of_birth": "date_of_birth",
        "profile_picture_url": "profile_picture_url",
    }
    updates = [(allowed[k], v) for k, v in fields.items() if k in allowed]
    if not updates:
        raise ApiError("validation_error", "No editable profile field was supplied.", 422)
    assignments = ",".join(f"{column}=%s" for column, _ in updates)
    params = [value for _, value in updates] + [user_id]
    with database.transaction() as conn, conn.cursor() as cur:
        cur.execute(f"UPDATE users SET {assignments} WHERE id=%s AND is_active RETURNING id", params)
        if not cur.fetchone():
            raise NotFound("Active user not found.")
        audit(
            conn,
            actor_user_id=user_id,
            action="user.profile.update",
            resource_type="user",
            resource_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"fields": [column for column, _ in updates]},
        )
    cache.delete(f"profile:{user_id}")
    return get_profile(user_id, use_cache=False)


def _verified_contact(account: dict[str, Any]) -> str | None:
    preferred = str(account.get("preferred_login") or "")
    if preferred == "email" and account.get("email") and account.get("email_verified_at"):
        return str(account["email"])
    if preferred == "phone" and account.get("phone") and account.get("phone_verified_at"):
        return str(account["phone"])
    if account.get("email") and account.get("email_verified_at"):
        return str(account["email"])
    if account.get("phone") and account.get("phone_verified_at"):
        return str(account["phone"])
    return None


def request_password_change_otp(user_id: int, ip: str) -> dict[str, Any]:
    row = database.fetch_one(
        """
        SELECT email::text AS email,phone,preferred_login,
               email_verified_at,phone_verified_at
        FROM users WHERE id=%s AND is_active
        """,
        (user_id,),
    )
    if not row:
        raise NotFound("Active user not found.")
    contact = _verified_contact(row)
    if not contact:
        raise ApiError(
            "contact_unavailable",
            "No verified contact is available for password confirmation.",
            409,
        )
    return OtpService.request(str(contact), f"password_change:{user_id}", ip=ip)


def change_password(
    user_id: int,
    current_password: str,
    new_password: str,
    otp_code: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    """Change the password after current-password and OTP confirmation."""
    account = database.fetch_one(
        """
        SELECT email::text AS email,phone,preferred_login,
               email_verified_at,phone_verified_at
        FROM users
        WHERE id=%s AND is_active AND password_hash=crypt(%s,password_hash)
        """,
        (user_id, current_password),
    )
    if not account:
        raise AuthenticationError("Current password is incorrect.")
    contact = _verified_contact(account)
    if not contact:
        raise ApiError("contact_unavailable", "No contact is available for OTP verification.", 409)
    OtpService.verify(str(contact), otp_code, f"password_change:{user_id}")

    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET password_hash=crypt(%s,gen_salt('bf',12)),
                session_version=session_version+1
            WHERE id=%s AND is_active AND password_hash=crypt(%s,password_hash)
            RETURNING id
            """,
            (new_password, user_id, current_password),
        )
        if not cur.fetchone():
            raise AuthenticationError("Current password is incorrect.")
        audit(
            conn,
            actor_user_id=user_id,
            action="user.password.change",
            resource_type="user",
            resource_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
        )
    cache.delete(f"profile:{user_id}")
    cache.revoke_user_refresh_tokens(user_id)
    profile = get_profile(user_id, use_cache=False)
    return {"profile": profile, "tokens": TokenService.issue_pair(profile)}


def request_contact_change(user_id: int, contact: str, ip: str) -> dict[str, Any]:
    kind, normalized = OtpService.normalize_contact(contact)
    existing = database.fetch_one(
        "SELECT id FROM users WHERE lower(email::text)=lower(%s) OR phone=%s",
        (normalized, normalized),
    )
    if existing and existing["id"] != user_id:
        raise Conflict("This contact is already used by another account.")
    result = OtpService.request(normalized, f"contact_change:{user_id}", ip=ip)
    result["contact_type"] = kind
    return result


def confirm_contact_change(
    user_id: int,
    contact: str,
    code: str,
    preferred_login: str,
    *,
    request_id: str | None,
    ip_address: str,
) -> dict[str, Any]:
    kind, normalized = OtpService.normalize_contact(contact)
    if preferred_login not in {"email", "phone"}:
        raise ApiError("validation_error", "preferred_login must be email or phone.", 422)

    account = database.fetch_one(
        "SELECT email::text AS email, phone FROM users WHERE id=%s AND is_active",
        (user_id,),
    )
    if not account:
        raise NotFound("Active user not found.")
    if preferred_login != kind and not account.get(preferred_login):
        raise ApiError(
            "validation_error",
            f"Cannot prefer {preferred_login} login because that contact is not set.",
            422,
            {"field": "preferred_login"},
        )

    OtpService.verify(normalized, code, f"contact_change:{user_id}")
    column = "email" if kind == "email" else "phone"
    verified_column = "email_verified_at" if kind == "email" else "phone_verified_at"
    with database.transaction(isolation="SERIALIZABLE") as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            UPDATE users
            SET {column}=%s, {verified_column}=CURRENT_TIMESTAMP,
                preferred_login=%s, session_version=session_version+1
            WHERE id=%s AND is_active
            RETURNING id
            """,
            (normalized, preferred_login, user_id),
        )
        if not cur.fetchone():
            raise NotFound("Active user not found.")
        audit(
            conn,
            actor_user_id=user_id,
            action="user.contact.change",
            resource_type="user",
            resource_id=user_id,
            request_id=request_id,
            ip_address=ip_address,
            metadata={"contact_type": kind},
        )
    cache.delete(f"profile:{user_id}")
    cache.revoke_user_refresh_tokens(user_id)
    profile = get_profile(user_id, use_cache=False)
    return {"profile": profile, "tokens": TokenService.issue_pair(profile)}
