from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from config import config


ROOT = Path(__file__).resolve().parent.parent


def test_pool_bounds_and_token_lifetimes_are_positive() -> None:
    assert 0 <= config.db_pool_min <= config.db_pool_max
    assert config.access_token_minutes >= 1
    assert config.refresh_token_days >= 1
    assert config.otp_ttl_seconds >= 60


def test_example_environment_uses_independent_secrets() -> None:
    values: dict[str, str] = {}
    for raw in Path(".env.example").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value

    assert values["JWT_SECRET"] != values["OTP_HMAC_SECRET"]
    assert values["DJANGO_SECRET_KEY"] != values["JWT_SECRET"]


def _production_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "DJANGO_SECRET_KEY": "d" * 48,
            "JWT_SECRET": "j" * 48,
            "OTP_HMAC_SECRET": "o" * 48,
            "OTP_DEBUG_RETURN_CODE": "false",
            "ALLOW_LOCAL_WALLET_TOP_UP": "false",
            "CORS_ALLOW_ALL": "false",
            "OTP_EMAIL_ENABLED": "false",
            "OTP_SMS_WEBHOOK_URL": "https://sms.example.test/send",
        }
    )
    return env


def test_safe_production_configuration_is_accepted() -> None:
    process = subprocess.run(
        [sys.executable, "-c", "import config; config.validate_production_config(False)"],
        cwd=ROOT,
        env=_production_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr


def test_shared_jwt_and_otp_secret_is_rejected_in_production() -> None:
    env = _production_env()
    env["OTP_HMAC_SECRET"] = env["JWT_SECRET"]

    process = subprocess.run(
        [sys.executable, "-c", "import config; config.validate_production_config(False)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode != 0
    assert "OTP_HMAC_SECRET_MUST_DIFFER_FROM_JWT_SECRET" in (
        process.stderr + process.stdout
    )


def test_elasticsearch_defaults_are_safe_and_bounded() -> None:
    assert config.elasticsearch_timeout_seconds >= 1
    assert config.elasticsearch_sync_batch_size >= 1
    assert config.elasticsearch_outbox_batch_size >= 1
    assert config.elasticsearch_full_sync_seconds >= 60
    assert config.elasticsearch_outbox_retention_days >= 1
    assert config.elasticsearch_index == config.elasticsearch_index.lower()


def test_invalid_elasticsearch_production_configuration_is_rejected() -> None:
    env = _production_env()
    env.update(
        {
            "ELASTICSEARCH_ENABLED": "true",
            "ELASTICSEARCH_URL": "not-a-url",
            "ELASTICSEARCH_INDEX": "INVALID INDEX",
        }
    )

    process = subprocess.run(
        [sys.executable, "-c", "import config; config.validate_production_config(False)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode != 0
    output = process.stderr + process.stdout
    assert "ELASTICSEARCH_URL" in output
    assert "ELASTICSEARCH_INDEX" in output


def test_conflicting_elasticsearch_auth_is_rejected_in_production() -> None:
    env = _production_env()
    env.update(
        {
            "ELASTICSEARCH_ENABLED": "true",
            "ELASTICSEARCH_URL": "https://search.example.test",
            "ELASTICSEARCH_API_KEY": "test-api-key",
            "ELASTICSEARCH_USERNAME": "user",
            "ELASTICSEARCH_PASSWORD": "password",
        }
    )

    process = subprocess.run(
        [sys.executable, "-c", "import config; config.validate_production_config(False)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode != 0
    assert "ELASTICSEARCH_AUTH_CONFLICT" in (
        process.stderr + process.stdout
    )


def test_elasticsearch_credentials_require_https_in_production() -> None:
    env = _production_env()
    env.update(
        {
            "ELASTICSEARCH_ENABLED": "true",
            "ELASTICSEARCH_URL": "http://search.example.test",
            "ELASTICSEARCH_API_KEY": "test-api-key",
        }
    )

    process = subprocess.run(
        [sys.executable, "-c", "import config; config.validate_production_config(False)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode != 0
    assert "ELASTICSEARCH_AUTH_REQUIRES_HTTPS" in (
        process.stderr + process.stdout
    )