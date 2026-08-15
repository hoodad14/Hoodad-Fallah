"""Dependency-free audit for the final flat ArenaPass delivery package."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_VERSION = "3.1.0"
REQUIRED_FILES = {
    ".dockerignore",
    ".env.example",
    ".gitignore",
    "00_schema.sql",
    "01_seed_data.sql",
    "02_required_queries.sql",
    "03_required_functions.sql",
    "04_business_functions.sql",
    "05_validation_tests.sql",
    "06_backend_extensions.sql",
    "99_bootstrap_complete.sql",
    "manage.py",
    "settings.py",
    "urls.py",
    "views.py",
    "worker.py",
    "search_engine.py",
    "services_chat.py",
    "Dockerfile",
    "Dockerfile.frontend",
    "nginx.conf",
    "docker-compose.yml",
    "README.md",
    "openapi.json",
    "ArenaPass.postman_collection.json",
    "پروژه پایانی درس(14).pdf",
    "پروژه پایانی درس(15).pdf",
    "index.html",
    "styles.css",
    "app.js",
    "i18n.js",
    "FRONTEND_README.md",
    "FRONTEND_VERIFICATION_REPORT.md",
    "AUTHENTICATION_GUIDE.md",
    "AUTHENTICATION_VERIFICATION_REPORT.md",
    "auth_mailpit_smoke.py",
    "frontend-preview-desktop.png",
    "frontend-preview-mobile.png",
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
ENV_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def fail(message: str) -> None:
    raise AssertionError(message)


def check_flat_layout() -> None:
    nested = sorted(path.name for path in ROOT.iterdir() if path.is_dir())
    if nested:
        fail(f"Nested directories are not allowed: {nested}")
    unwanted = sorted(path.name for path in ROOT.iterdir() if path.suffix == ".pyc")
    if unwanted:
        fail(f"Compiled temporary files found: {unwanted}")
    missing = sorted(REQUIRED_FILES - {path.name for path in ROOT.iterdir() if path.is_file()})
    if missing:
        fail(f"Missing required files: {missing}")


def check_python() -> None:
    for path in sorted(ROOT.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, path.name, "exec")
        ast.parse(source, filename=path.name)


def check_json_and_version() -> None:
    openapi = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    postman = json.loads(
        (ROOT / "ArenaPass.postman_collection.json").read_text(encoding="utf-8")
    )
    if openapi.get("openapi") != "3.1.0":
        fail("OpenAPI document is not version 3.1.0")
    if openapi.get("info", {}).get("version") != EXPECTED_VERSION:
        fail("OpenAPI release version is inconsistent")
    if EXPECTED_VERSION not in postman.get("info", {}).get("name", ""):
        fail("Postman release version is inconsistent")
    if f'VERSION = "{EXPECTED_VERSION}"' not in (ROOT / "version.py").read_text(encoding="utf-8"):
        fail("version.py is inconsistent")
    if EXPECTED_VERSION not in (ROOT / "Dockerfile").read_text(encoding="utf-8"):
        fail("Dockerfile release version is inconsistent")
    if EXPECTED_VERSION not in (ROOT / "docker-compose.yml").read_text(encoding="utf-8"):
        fail("Compose image release version is inconsistent")



def check_frontend() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    i18n = (ROOT / "i18n.js").read_text(encoding="utf-8")
    if '<html lang="fa" dir="rtl"' not in html:
        fail("Frontend document must be Persian RTL")
    if not re.search(r'href=["\']styles\.css(?:\?[^"\']*)?["\']', html):
        fail('Frontend stylesheet reference is missing')
    if not re.search(r'src=["\']app\.js(?:\?[^"\']*)?["\']', html):
        fail('Frontend JavaScript reference is missing')
    if not re.search(r'src=["\']i18n\.js(?:\?[^"\']*)?["\']', html):
        fail('Bilingual language runtime is not loaded')
    if 'id="languageButton"' not in html or 'id="languageButtonLabel"' not in html or 'language-button' not in css:
        fail('FA/EN language switch is missing')
    if html.index('i18n.js') > html.index('app.js'):
        fail('i18n.js must load before app.js')
    frontend_dockerfile = (ROOT / 'Dockerfile.frontend').read_text(encoding='utf-8')
    if 'i18n.js' not in frontend_dockerfile:
        fail('Dockerized frontend does not include i18n.js')
    for token in ('arenapass_language', 'function setLocale', 'function toggle', 'MutationObserver', "document.documentElement.dir"):
        if token not in i18n:
            fail(f'Bilingual runtime is incomplete: {token}')
    if "position:fixed" not in css.replace(" ", "") or "support-chat-dock" not in css:
        fail('Support-chat launcher must use stable viewport positioning')
    if "window.addEventListener('scroll', handleSupportChatScroll" not in js or "--chat-drag-y" not in css:
        fail('Support-chat launcher scroll-drag motion is missing')
    if "preventScroll: true" not in js or "scrollTop = window.scrollY" not in js:
        fail('Support-chat close behavior must preserve focus and page scroll')
    if re.search(r'<(?:script|link)[^>]+(?:src|href)=["\']https?://', html, re.I):
        fail("Frontend must not rely on external runtime assets")
    if "DEFAULT_API_BASE" not in js or "/api/v1" not in js:
        fail("Frontend API configuration is missing")
    if "document.addEventListener('DOMContentLoaded', init)" not in js:
        fail("Frontend initialization hook is missing")
    if "[hidden]{display:none!important}" not in css.replace(" ", ""):
        fail("Frontend hidden-state safety rule is missing")
    for auth_id in (
        "passwordLoginForm", "otpRequestForm", "otpVerifyForm",
        "signupForm", "signupVerifyForm", "otpResendButton",
        "signupResendButton",
    ):
        if f'id="{auth_id}"' not in html:
            fail(f"Frontend authentication control is missing: {auth_id}")
    for endpoint in (
        "/auth/password/login", "/auth/otp/request", "/auth/otp/verify",
        "/auth/signup", "/auth/signup/resend", "/auth/signup/verify",
    ):
        if endpoint not in js:
            fail(f"Frontend authentication endpoint is missing: {endpoint}")
    if "local_mailbox_url: null" not in js or "safeSessionSet('arenapass_pending_signup'" not in js:
        fail("Frontend signup/email flow is not storage-safe or provider-aware")
    if js.index("verify.hidden = false") > js.index("safeSessionSet('arenapass_pending_signup'"):
        fail("Signup verification UI must render before session storage")
    for chat_id in ("supportChatDock", "supportChatLauncher", "supportChatPanel", "supportChatForm"):
        if f'id="{chat_id}"' not in html:
            fail(f"Frontend support-chat control is missing: {chat_id}")
    for endpoint in ("/support-chat", "/support/chats"):
        if endpoint not in js:
            fail(f"Frontend support-chat endpoint is missing: {endpoint}")
    if len(html) < 10_000 or len(css) < 20_000 or len(js) < 50_000:
        fail("Frontend assets appear unexpectedly incomplete")

def check_env() -> None:
    name = ".env.example"
    path = ROOT / name
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not ENV_LINE.fullmatch(line):
            fail(f"Invalid environment syntax in {name}:{line_number}: {line!r}")
        key = line.split("=", 1)[0]
        if key in seen:
            fail(f"Duplicate environment key {key!r} in {name}")
        seen.add(key)
    if (ROOT / ".env").exists():
        fail("Runtime .env must not be included in the delivery package")
    if (ROOT / "env.example").exists():
        fail("Duplicate env.example must not be included")


def check_no_orm() -> None:
    forbidden = (
        "django.db.models",
        ".objects.",
        "models.Model",
        "ModelSerializer",
    )
    for path in ROOT.glob("*.py"):
        if path.name.startswith("test_") or path.name == "delivery_audit.py":
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                fail(f"Forbidden ORM token {token!r} found in {path.name}")


def check_sql_contract() -> None:
    schema = (ROOT / "00_schema.sql").read_text(encoding="utf-8").lower()
    queries = (ROOT / "02_required_queries.sql").read_text(encoding="utf-8").lower()
    functions = (ROOT / "03_required_functions.sql").read_text(encoding="utf-8").lower()
    business = (ROOT / "04_business_functions.sql").read_text(encoding="utf-8").lower()
    validation = (ROOT / "05_validation_tests.sql").read_text(encoding="utf-8").lower()
    extensions = (ROOT / "06_backend_extensions.sql").read_text(encoding="utf-8").lower()
    for table in (
        "users", "tickets", "reservations", "payments", "reports",
        "cancellation_requests", "refunds", "seat_change_requests",
    ):
        if f"create table {table}" not in schema:
            fail(f"Core table {table} is missing")
    if len(set(re.findall(r"--\s*q(\d+)\)", queries))) < 22:
        fail("The mandatory analytical-query file does not expose 22 numbered queries")
    if len(re.findall(r"create\s+(?:or\s+replace\s+)?function", functions)) < 8:
        fail("The mandatory stored-function file exposes fewer than eight functions")
    for name in ("reserve_ticket", "process_payment", "expire_pending_reservations"):
        if f"function {name}" not in business:
            fail(f"Business function {name} is missing")
    if "if v_count<10" not in validation:
        fail("The ten-row-per-table seed validation is missing")
    if "search_sync_outbox" not in extensions or "api_audit_log" not in extensions:
        fail("Backend extension/audit/search schema is incomplete")
    for chat_table in ("support_conversations", "support_messages"):
        if f"create table if not exists {chat_table}" not in extensions:
            fail(f"Support chat table {chat_table} is missing")


def check_shell_and_compose() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("db:", "redis:", "mailpit:", "backend:", "worker:", "frontend:"):
        if service not in compose:
            fail(f"Compose service {service} is missing")
    if "Dockerfile.frontend" not in compose or "nginx.conf" not in (ROOT / "Dockerfile.frontend").read_text(encoding="utf-8"):
        fail("Frontend container or reverse-proxy configuration is missing")
    for required_auth_wiring in (
        "axllent/mailpit:v1.30.6",
        "MP_WEBROOT: /mailpit/",
        "MP_SEND_API_AUTH_ACCEPT_ANY",
        'EMAIL_DELIVERY_MODE: ${EMAIL_DELIVERY_MODE:-smtp}',
        'EMAIL_HOST: ${EMAIL_HOST:-smtp.gmail.com}',
        'EMAIL_PORT: ${EMAIL_PORT:-587}',
        'EMAIL_USE_TLS: ${EMAIL_USE_TLS:-true}',
        'MAILPIT_API_URL: ${MAILPIT_API_URL:-http://mailpit:8025/mailpit}',
        'PUBLIC_MAILPIT_URL: ${PUBLIC_MAILPIT_URL:-}',
    ):
        if required_auth_wiring not in compose:
            fail(f"Compose authentication wiring is missing: {required_auth_wiring}")
    if '127.0.0.1:${MAILPIT_UI_PORT' in compose:
        fail("Mailpit must be served through the same-origin Nginx proxy, not a stale host port")
    notifications = (ROOT / "notifications.py").read_text(encoding="utf-8")
    nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    if "api/v1/send" not in notifications or "api/v1/message/{encoded_id}" not in notifications:
        fail("Deterministic Mailpit send/persistence verification is missing")
    if not re.search(r"location\s+(?:\^~\s+)?/mailpit/", nginx) or "proxy_set_header Host $http_host" not in nginx:
        fail("Same-origin Mailpit reverse proxy is incomplete")
    if "required: false" in compose or re.search(r"env_file:\s*\n\s*-\s*path:", compose):
        fail("Compose uses the newer env_file long syntax and may fail on older Compose releases")
    for path in ROOT.glob("*.sh"):
        first = path.read_text(encoding="utf-8").splitlines()[0]
        if not first.startswith("#!"):
            fail(f"Shell script {path.name} has no shebang")



def check_checksum_inventory() -> None:
    checksum_path = ROOT / "SHA256SUMS.txt"
    if not checksum_path.is_file():
        fail("SHA256SUMS.txt is missing")
    listed: dict[str, str] = {}
    for line_number, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            digest, name = line.split("  ", 1)
        except ValueError as exc:
            fail(f"Malformed checksum line {line_number}")
            raise exc
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"Malformed SHA-256 digest on line {line_number}")
        listed[name] = digest
    expected_names = {
        path.name for path in ROOT.iterdir()
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    if set(listed) != expected_names:
        fail(
            "Checksum inventory mismatch: "
            f"missing={sorted(expected_names - set(listed))}, "
            f"extra={sorted(set(listed) - expected_names)}"
        )
    for name, expected in listed.items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            fail(f"Checksum mismatch for {name}")


def check_manifest() -> None:
    manifest = (ROOT / "PROJECT_MANIFEST.txt").read_text(encoding="utf-8")
    if "Backend v3.1.0" not in manifest or "Frontend v1.7.0" not in manifest or "درس(15).pdf" not in manifest:
        fail("Project manifest release/spec metadata is stale")
    total = len([path for path in ROOT.iterdir() if path.is_file()])
    if f"Total files in final folder: {total}" not in manifest:
        fail("Project manifest file count is stale")


def write_digest_summary() -> None:
    digest = hashlib.sha256()
    for path in sorted(ROOT.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name not in {"SHA256SUMS.txt", "PROJECT_MANIFEST.txt"}:
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
    print(f"Package content digest: {digest.hexdigest()}")


def main() -> int:
    checks = (
        check_flat_layout,
        check_python,
        check_json_and_version,
        check_frontend,
        check_env,
        check_no_orm,
        check_sql_contract,
        check_shell_and_compose,
        check_manifest,
        check_checksum_inventory,
    )
    try:
        for check in checks:
            check()
            print(f"PASS  {check.__name__}")
        write_digest_summary()
    except Exception as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print("ArenaPass flat delivery audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
