from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE_ROOT = ROOT / "database"
DOCS_ROOT = ROOT / "docs"
POSTMAN_ROOT = ROOT / "postman"
HTTP_METHODS = {"get", "post", "patch", "delete", "put"}


def _view_methods() -> dict[str, set[str]]:
    tree = ast.parse((ROOT / "views.py").read_text(encoding="utf-8"))
    result: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "endpoint"
                and decorator.args
                and isinstance(decorator.args[0], (ast.Set, ast.List, ast.Tuple))
            ):
                continue
            result[node.name] = {
                str(item.value).lower()
                for item in decorator.args[0].elts
                if isinstance(item, ast.Constant)
            }
    return result


def _registered_operations() -> set[tuple[str, str]]:
    methods = _view_methods()
    tree = ast.parse((ROOT / "urls.py").read_text(encoding="utf-8"))
    result: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "path"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[1], ast.Attribute)
        ):
            continue
        route = "/" + str(node.args[0].value)
        route = re.sub(r"<int:([^>]+)>", r"{\1}", route)
        view_name = node.args[1].attr
        for method in methods.get(view_name, set()):
            result.add((method, route))
    return result


def _openapi_operations() -> set[tuple[str, str]]:
    document = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    return {
        (method.lower(), path)
        for path, item in document["paths"].items()
        for method in item
        if method.lower() in HTTP_METHODS
    }


def _postman_operations() -> set[tuple[str, str]]:
    document = json.loads(
        (POSTMAN_ROOT / "ArenaPass.postman_collection.json").read_text(encoding="utf-8")
    )
    operations: set[tuple[str, str]] = set()

    def walk(items: list[dict[str, object]]) -> None:
        for item in items:
            children = item.get("item")
            if isinstance(children, list):
                walk(children)
                continue
            request = item.get("request")
            if not isinstance(request, dict):
                continue
            url = request.get("url")
            if not isinstance(url, dict):
                continue
            raw = str(url.get("raw", "")).replace("{{base_url}}", "")
            raw = raw.split("?", 1)[0]
            raw = re.sub(r"\{\{([^}]+)\}\}", r"{\1}", raw)
            operations.add((str(request["method"]).lower(), raw))

    walk(document["item"])
    return operations


def test_python_files_compile() -> None:
    for path in ROOT.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_backend_never_uses_django_orm() -> None:
    forbidden = (".objects.", "models.Model", "django.db.models", "ModelSerializer")
    for path in ROOT.glob("*.py"):
        if path.name.startswith("test_") or path.name == "delivery_audit.py":
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"ORM token {token!r} found in {path.name}"


def test_required_delivery_assets_exist() -> None:
    required_root = {
        "version.py",
        "search_engine.py",
        "services_chat.py",
        "sync_search_index.py",
        "Dockerfile",
        "Dockerfile.frontend",
        "nginx.conf",
        "docker-compose.yml",
        ".env.example",
        "openapi.json",
        "auth_mailpit_smoke.py",
    }

    required_database = {
        "00_schema.sql",
        "01_seed_data.sql",
        "02_required_queries.sql",
        "03_required_functions.sql",
        "04_business_functions.sql",
        "05_validation_tests.sql",
        "06_backend_extensions.sql",
    }

    required_docs = {
        "ELASTICSEARCH.md",
        "README.md",
        "SECURITY.md",
        "TESTING.md",
        "AUTHENTICATION_GUIDE.md",
    }

    required_postman = {
        "ArenaPass.postman_collection.json",
    }

    assert required_root <= {
        path.name
        for path in ROOT.iterdir()
        if path.is_file()
    } | {
        path.name
        for path in (ROOT / "scripts").iterdir()
        if path.is_file()
    }

    assert required_database <= {
        path.name for path in DATABASE_ROOT.iterdir() if path.is_file()
    }

    assert required_docs <= {
        path.name for path in DOCS_ROOT.iterdir() if path.is_file()
    }

    assert required_postman <= {
        path.name for path in POSTMAN_ROOT.iterdir() if path.is_file()
    }


def test_no_upload_suffix_sql_files_remain() -> None:
    assert not [
        path.name
        for path in ROOT.glob("*.sql")
        if re.search(r"\(\d+\)\.sql$", path.name)
    ]


def test_business_functions_are_present() -> None:
    sql = (DATABASE_ROOT / "04_business_functions.sql").read_text(encoding="utf-8").lower()
    for name in (
        "reserve_ticket",
        "process_payment",
        "expire_pending_reservations",
        "top_up_wallet",
        "request_cancellation",
        "review_cancellation",
        "request_seat_change",
        "review_seat_change",
        "deactivate_user",
    ):
        assert f"function {name}" in sql


def test_backend_extension_contains_security_and_audit_schema() -> None:
    sql = (DATABASE_ROOT / "06_backend_extensions.sql").read_text(encoding="utf-8").lower()
    assert "session_version" in sql
    assert "email_verified_at" in sql
    assert "phone_verified_at" in sql
    assert "last_login_at" in sql
    assert "support_review_status" in sql
    assert "api_audit_log" in sql
    assert "support_cancel_reservation" in sql
    assert "search_sync_outbox" in sql
    assert "enqueue_ticket_search_sync" in sql
    assert "support_conversations" in sql
    assert "support_messages" in sql
    assert "validate_support_message_sender" in sql
    for trigger in (
        "search_sync_ticket",
        "search_sync_ticket_amenity",
        "search_sync_match",
        "search_sync_team",
        "search_sync_sport",
        "search_sync_venue",
        "search_sync_city",
        "search_sync_province",
        "search_sync_organizer",
        "search_sync_category",
        "search_sync_amenity",
    ):
        assert f"create trigger {trigger}" in sql


def test_support_chat_contract_is_complete() -> None:
    services = (ROOT / "services_chat.py").read_text(encoding="utf-8")
    views = (ROOT / "views.py").read_text(encoding="utf-8")
    urls = (ROOT / "urls.py").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    for token in (
        "get_spectator_chat", "send_spectator_message",
        "list_support_conversations", "send_support_message",
        "set_conversation_status",
    ):
        assert f"def {token}" in services
    for token in ("support_chat_message", "support_chats", "support_chat_reply"):
        assert f"def {token}" in views
    assert 'path("api/v1/support-chat"' in urls
    assert 'path("api/v1/support/chats"' in urls
    for control in ("supportChatDock", "supportChatLauncher", "supportChatPanel", "supportChatForm"):
        assert f'id="{control}"' in html
    assert "position:fixed" in css.replace(" ", "")
    assert "positionSupportChatDock" in frontend
    assert "handleSupportChatScroll" in frontend
    assert "--chat-drag-y" in css
    assert "/support-chat/messages" in frontend
    assert "/support/chats/${id}/messages" in frontend


def test_routes_openapi_and_postman_are_exactly_aligned() -> None:
    registered = _registered_operations()
    assert len(registered) == 66
    assert _openapi_operations() == registered
    assert _postman_operations() == registered


def test_openapi_and_postman_json_are_valid_and_current() -> None:
    openapi = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    postman = json.loads(
        ((POSTMAN_ROOT / "ArenaPass.postman_collection.json")).read_text(encoding="utf-8")
    )
    assert openapi["openapi"] == "3.1.0"
    assert openapi["info"]["version"] == "3.1.0"
    assert "3.1.0" in postman["info"]["name"]
    assert "{{{base_url}}}" not in json.dumps(postman)


def test_compose_uses_canonical_sql_assets_and_separate_worker() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for name in (
        "00_schema.sql",
        "01_seed_data.sql",
        "02_required_queries.sql",
        "03_required_functions.sql",
        "04_business_functions.sql",
        "06_backend_extensions.sql",
        "05_validation_tests.sql",
    ):
        assert name in compose
    assert "06_validation_tests.sql" in compose
    assert re.search(r"(?m)^\s{2}worker:\s*$", compose)
    assert re.search(r"(?m)^\s{2}elasticsearch:\s*$", compose)
    assert 'profiles: ["search"]' in compose
    assert re.search(r"(?m)^\s{2}mailpit:\s*$", compose)
    assert "axllent/mailpit:v1.30.6" in compose
    assert "MP_WEBROOT: /mailpit/" in compose
    assert "MP_SEND_API_AUTH_ACCEPT_ANY" in compose
    assert 'EMAIL_DELIVERY_MODE: ${EMAIL_DELIVERY_MODE:-smtp}' in compose
    assert 'EMAIL_HOST: ${EMAIL_HOST:-smtp.gmail.com}' in compose
    assert 'EMAIL_PORT: ${EMAIL_PORT:-587}' in compose
    assert 'EMAIL_USE_TLS: ${EMAIL_USE_TLS:-true}' in compose
    assert 'MAILPIT_API_URL: ${MAILPIT_API_URL:-http://mailpit:8025/mailpit}' in compose
    assert 'PUBLIC_MAILPIT_URL: ${PUBLIC_MAILPIT_URL:-}' in compose
    assert '127.0.0.1:${MAILPIT_UI_PORT' not in compose
    assert "docker.elastic.co/elasticsearch/elasticsearch:9.4.4" in compose
    assert "arenapass_elasticsearch_data" in compose



def test_mailpit_delivery_and_signup_transition_are_deterministic() -> None:
    notifications = (ROOT / "notifications.py").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'api/v1/send' in notifications
    assert 'api/v1/message/{encoded_id}' in notifications
    assert 'delivery_message_id' in (ROOT / "authentication.py").read_text(encoding="utf-8")
    assert 'MP_WEBROOT: /mailpit/' in compose
    assert re.search(r'location\s+(?:\^~\s+)?/mailpit/', nginx)
    assert 'proxy_set_header Host $http_host' in nginx
    assert "connect-src 'self' http: https: ws: wss:" in nginx
    assert "local_mailbox_url: '/mailpit/'" in frontend
    assert 'mailpitMessageUrl' in frontend
    assert 'delivery_message_id' in frontend
    assert "safeSessionSet('arenapass_pending_signup'" in frontend
    assert frontend.index('verify.hidden = false') < frontend.index("safeSessionSet('arenapass_pending_signup'")
    assert 'http://127.0.0.1:8025' not in frontend

def test_security_contracts_are_wired() -> None:
    auth = (ROOT / "authentication.py").read_text(encoding="utf-8")
    views = (ROOT / "views.py").read_text(encoding="utf-8")
    config = (ROOT / "config.py").read_text(encoding="utf-8")
    assert '"sv"' in auth
    assert "session_version" in auth
    assert "otp_hmac_secret" in auth
    assert "ensure_allowed_fields" in views
    assert "ALLOW_LOCAL_WALLET_TOP_UP" in (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "allow_local_wallet_top_up" in config


def test_every_custom_database_function_called_by_python_exists() -> None:
    python_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROOT.glob("*.py")
        if not path.name.startswith("test_")
    )
    called = {
        name.lower()
        for name in re.findall(
            r"(?:FROM|SELECT)\s+([a-z_][a-z0-9_]*)\s*\(",
            python_source,
            flags=re.I,
        )
    }
    sql_source = "\n".join(
        (DATABASE_ROOT / name).read_text(encoding="utf-8")
        for name in (
            "00_schema.sql",
            "03_required_functions.sql",
            "04_business_functions.sql",
            "06_backend_extensions.sql",
        )
    )
    defined = {
        name.lower()
        for name in re.findall(
            r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([a-z_][a-z0-9_]*)\s*\(",
            sql_source,
            flags=re.I,
        )
    }
    PostgreSQL_builtins = {
        "count",
        "coalesce",
        "jsonb_agg",
        "jsonb_build_object",
        "to_jsonb",
        "round",
        "date_trunc",
        "lower",
        "crypt",
        "gen_salt",
        "to_regclass",
        "to_regprocedure",
        "set_config",
        "pg_advisory_lock",
        "pg_advisory_unlock",
        "exists",
    }
    assert called - PostgreSQL_builtins <= defined


def test_delivery_version_is_consistent() -> None:
    expected = "3.1.0"
    version_source = (ROOT / "version.py").read_text(encoding="utf-8")
    assert f'VERSION = "{expected}"' in version_source
    assert "from version import SERVICE_NAME, VERSION" in (ROOT / "views.py").read_text(encoding="utf-8")
    assert expected in (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))["info"]["version"] == expected
    assert expected in json.loads(
        (POSTMAN_ROOT / "ArenaPass.postman_collection.json").read_text(encoding="utf-8")
    )["info"]["name"]


def test_elasticsearch_search_sync_contract_is_complete() -> None:
    engine = (ROOT / "search_engine.py").read_text(encoding="utf-8")
    worker = (ROOT / "worker.py").read_text(encoding="utf-8")
    catalog = (ROOT / "services_catalog.py").read_text(encoding="utf-8")
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    validation = (DATABASE_ROOT / "05_validation_tests.sql").read_text(encoding="utf-8")
    engine_compact = re.sub(r"\s+", "", engine)

    assert '"dynamic":"strict"' in engine_compact
    for token in (
        "def full_sync",
        "def process_outbox",
        "def cleanup_outbox",
        "def search_tickets",
        "pg_advisory_lock",
        "track_total_hits",
        "phrase_prefix",
    ):
        assert token in engine
    assert "search_engine.process_outbox" in worker
    assert "full_sync(only_if_missing=True)" in worker
    assert "elasticsearch_fallback_to_sql" in catalog
    assert "python scripts/sync_search_index.py --full" in entrypoint
    assert "v_trigger_count<>11" in validation


def test_final_hardening_contracts_are_present() -> None:
    settings_source = (ROOT / "settings.py").read_text(encoding="utf-8")
    middleware_source = (ROOT / "middleware.py").read_text(encoding="utf-8")
    views_source = (ROOT / "views.py").read_text(encoding="utf-8")
    catalog_source = (ROOT / "services_catalog.py").read_text(encoding="utf-8")
    schema_source = (DATABASE_ROOT / "00_schema.sql").read_text(encoding="utf-8")
    business_source = (DATABASE_ROOT / "04_business_functions.sql").read_text(encoding="utf-8")

    assert "django.middleware.security.SecurityMiddleware" in settings_source
    urls_source = (ROOT / "urls.py").read_text(encoding="utf-8")
    for handler in ("handler400", "handler403", "handler404", "handler500"):
        assert handler in urls_source
    assert 'response["X-API-Version"]' in middleware_source
    assert "ensure_allowed_query_params" in views_source
    for column in (
        "sport_is_active",
        "home_team_is_active",
        "away_team_is_active",
        "organizer_is_active",
        "category_is_active",
    ):
        assert column in schema_source
        assert column in catalog_source
    assert "Only spectator accounts can be deactivated" in business_source

    existing_result = business_source.index("IF FOUND THEN", business_source.index("FUNCTION process_payment"))
    method_lookup = business_source.index("FROM payment_methods", business_source.index("FUNCTION process_payment"))
    assert existing_result < method_lookup


def test_v250_security_and_inventory_hardening_contracts() -> None:
    cache_source = (ROOT / "cache.py").read_text(encoding="utf-8")
    auth_source = (ROOT / "authentication.py").read_text(encoding="utf-8")
    support_source = (ROOT / "services_support.py").read_text(encoding="utf-8")
    views_source = (ROOT / "views.py").read_text(encoding="utf-8")
    schema_source = (DATABASE_ROOT / "00_schema.sql").read_text(encoding="utf-8")
    business_source = (DATABASE_ROOT / "04_business_functions.sql").read_text(encoding="utf-8")
    validation_source = (DATABASE_ROOT / "05_validation_tests.sql").read_text(encoding="utf-8")
    config_source = (ROOT / "config.py").read_text(encoding="utf-8")

    assert "retry_after_seconds" in auth_source
    assert "redis.call('TTL', KEYS[1])" in cache_source
    assert "refresh-family:" in cache_source
    assert "revoke_refresh_family" in cache_source
    assert "ELASTICSEARCH_AUTH_REQUIRES_HTTPS" in config_source

    for token in (
        "sport_active",
        "home_team_active",
        "away_team_active",
        "category_active",
    ):
        assert token in schema_source
        assert token in business_source
    assert "Inactive catalog entities block both new holds and payment completion" in validation_source

    assert "has_seat_change_holds" in support_source
    assert "change_held_quantity" in support_source
    assert "Use the dedicated DELETE endpoint to deactivate a ticket safely" in support_source
    assert "sale_starts_at" in schema_source and "sale_ends_at" in schema_source
    assert "Destination ticket sale has ended" in business_source
    assert "Report status cannot change from" in support_source
    assert "dict.fromkeys" in support_source
    assert "amenity_ids cannot contain more than 100 items" in views_source


def test_dependency_security_pins_are_current_for_this_delivery() -> None:
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    development = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "sqlparse==0.5.5" in runtime
    assert "pytest==9.1.1" in development
    assert "pytest==9.0.2" not in development


def test_delivery_is_flat_clean_and_env_files_are_valid() -> None:
    assert not [
        path.name for path in ROOT.iterdir()
        if path.is_dir()
        and path.name not in {
            "__pycache__",
            ".pytest_cache",
            ".venv",
            "assets",
            "database",
            "docs",
            "frontend",
            "postman",
            "scripts",
            "tests",
        }
    ]

    assert not list(ROOT.glob("*.pyc"))

    env_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()

    invalid = [
        (line_number, line)
        for line_number, line in enumerate(lines, start=1)
        if line.strip()
        and not line.lstrip().startswith("#")
        and not env_pattern.fullmatch(line)
    ]

    assert not invalid, f"Invalid environment syntax in .env.example: {invalid}"

    assert not (ROOT / "env.example").exists()

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "frontend:" in compose
    assert "Dockerfile.frontend" in compose
    assert "required: false" not in compose
    assert not re.search(r"env_file:\s*\n\s*-\s*path:", compose)


def test_seed_and_validation_cover_minimum_ten_rows_per_persistent_table() -> None:
    seed = (DATABASE_ROOT / "01_seed_data.sql").read_text(encoding="utf-8").lower()
    validation = (DATABASE_ROOT / "05_validation_tests.sql").read_text(encoding="utf-8").lower()
    for table in (
        "provinces", "cities", "venues", "users", "wallets", "sport_types",
        "teams", "organizers", "matches", "ticket_categories", "tickets",
        "amenities", "ticket_amenities", "reservations", "payment_methods",
        "payments", "wallet_transactions", "cancellation_policies",
        "cancellation_requests", "refunds", "seat_change_requests",
        "issued_tickets", "report_categories", "reports",
        "reservation_status_history",
    ):
        assert f"'{table}'" in validation
    assert "if v_count<10" in validation
    assert "10+ rows per table" in seed


def test_v300_final_validation_hardening_contracts() -> None:
    catalog = (ROOT / "services_catalog.py").read_text(encoding="utf-8")
    views = (ROOT / "views.py").read_text(encoding="utf-8")
    support = (ROOT / "services_support.py").read_text(encoding="utf-8")
    assert "candidate.sport_is_active" in catalog
    assert "candidate.category_is_active" in catalog
    assert "m.status IN ('scheduled','postponed')" in catalog
    assert "date_from cannot exceed date_to" in views
    assert "Numbered tickets require both row_code and seat_code" in support
    assert "total_capacity cannot be lower than already allocated inventory" in support
    assert "sale_ends_at must be later than sale_starts_at" in support
