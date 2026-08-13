"""Application exception hierarchy and PostgreSQL error translation."""
from __future__ import annotations

from dataclasses import dataclass

from psycopg import errors


@dataclass(slots=True)
class ApiError(Exception):
    code: str
    message: str
    status: int = 400
    details: object | None = None


class AuthenticationError(ApiError):
    def __init__(self, message: str = "Authentication is required.") -> None:
        super().__init__("authentication_required", message, 401)


class PermissionDenied(ApiError):
    def __init__(self, message: str = "You do not have permission for this operation.") -> None:
        super().__init__("permission_denied", message, 403)


class NotFound(ApiError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__("not_found", message, 404)


class Conflict(ApiError):
    def __init__(self, message: str, details: object | None = None) -> None:
        super().__init__("conflict", message, 409, details)


def map_database_error(exc: Exception) -> ApiError:
    message = getattr(getattr(exc, "diag", None), "message_primary", None) or str(exc)
    if isinstance(exc, errors.UniqueViolation):
        return Conflict("A record with the same unique value already exists.")
    if isinstance(exc, errors.ForeignKeyViolation):
        return ApiError("invalid_reference", "A referenced record does not exist.", 400)
    if isinstance(exc, errors.CheckViolation):
        return ApiError("constraint_violation", message, 400)
    if isinstance(
        exc,
        (errors.SerializationFailure, errors.DeadlockDetected, errors.LockNotAvailable),
    ):
        return Conflict("Concurrent update detected. Retry the request.")
    if isinstance(exc, errors.QueryCanceled):
        return ApiError(
            "database_timeout",
            "The database operation exceeded its safe time limit.",
            503,
        )
    if isinstance(exc, errors.RaiseException):
        lowered = message.lower()
        status = 409 if any(x in lowered for x in ("insufficient", "already", "expired", "cannot", "inconsistent")) else 400
        return ApiError("business_rule_violation", message, status)
    return ApiError("database_error", "The database rejected the operation.", 500)
