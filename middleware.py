"""Small dependency-free HTTP middleware set."""
from __future__ import annotations

import re
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers

from config import config
from version import VERSION

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")


class RequestIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        supplied = (request.headers.get("X-Request-ID") or "").strip()
        request.request_id = supplied if REQUEST_ID_RE.fullmatch(supplied) else str(uuid.uuid4())  # type: ignore[attr-defined]
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id  # type: ignore[attr-defined]
        return response


class CorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        origin = request.headers.get("Origin")
        allowed = config.allow_all_origins or (origin and origin in config.allowed_origins)
        if allowed:
            response["Access-Control-Allow-Origin"] = "*" if config.allow_all_origins else origin
            patch_vary_headers(response, ("Origin",))
            response["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, X-Request-ID"
            )
            response["Access-Control-Expose-Headers"] = (
                "X-Request-ID, X-API-Version, Retry-After"
            )
            response["Access-Control-Allow-Methods"] = (
                "GET, POST, PATCH, DELETE, OPTIONS"
            )
            response["Access-Control-Max-Age"] = "600"
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-API-Version"] = VERSION
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "no-referrer"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response["Cache-Control"] = response.get("Cache-Control", "no-store")
        # HTTPS redirect and HSTS are intentionally delegated to Django's
        # SecurityMiddleware so SECURE_SSL_REDIRECT/SECURE_HSTS_* settings work.
        return response
