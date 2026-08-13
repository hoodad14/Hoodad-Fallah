"""Redis cache, OTP store, token state, rate limits and worker markers."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis

from config import config

logger = logging.getLogger(__name__)
_client = redis.Redis.from_url(
    config.redis_url,
    decode_responses=True,
    socket_timeout=3,
    socket_connect_timeout=3,
    health_check_interval=30,
)


def client() -> redis.Redis:
    return _client


def ping() -> bool:
    try:
        return bool(_client.ping())
    except redis.RedisError:
        return False


def get_json(key: str) -> Any | None:
    try:
        raw = _client.get(key)
    except redis.RedisError:
        logger.exception("Redis get failed for %s", key)
        if config.redis_required:
            raise
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Corrupt cache entries must never turn a recoverable cache miss into a
        # failed API request. Delete and rebuild from PostgreSQL.
        logger.warning("Discarding malformed Redis JSON key=%s", key)
        try:
            _client.delete(key)
        except redis.RedisError:
            logger.exception("Redis delete failed for malformed key=%s", key)
            if config.redis_required:
                raise
        return None


def set_json(key: str, value: Any, ttl: int) -> None:
    try:
        _client.setex(
            key,
            ttl,
            json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":")),
        )
    except redis.RedisError:
        logger.exception("Redis set failed for %s", key)
        if config.redis_required:
            raise


def delete(*keys: str) -> None:
    if not keys:
        return
    try:
        _client.delete(*keys)
    except redis.RedisError:
        logger.exception("Redis delete failed")
        if config.redis_required:
            raise



def ttl(key: str) -> int:
    """Return a positive TTL in seconds, or zero when the key is absent/expired."""
    try:
        value = int(_client.ttl(key))
        return value if value > 0 else 0
    except redis.RedisError:
        logger.exception("Redis TTL failed for %s", key)
        if config.redis_required:
            raise
        return 0


def exists(key: str) -> bool:
    try:
        return bool(_client.exists(key))
    except redis.RedisError:
        logger.exception("Redis EXISTS failed for %s", key)
        if config.redis_required:
            raise
        return False


def set_once(key: str, value: str, ttl: int) -> bool:
    try:
        return bool(_client.set(key, value, ex=ttl, nx=True))
    except redis.RedisError:
        logger.exception("Redis SET NX failed for %s", key)
        if config.redis_required:
            raise
        return False


def bump_version(namespace: str) -> int:
    try:
        return int(_client.incr(f"cache-version:{namespace}"))
    except redis.RedisError:
        logger.exception("Redis version bump failed")
        if config.redis_required:
            raise
        return 0


def version(namespace: str) -> int:
    try:
        raw = _client.get(f"cache-version:{namespace}")
        return int(raw or 0)
    except ValueError:
        logger.warning("Resetting invalid cache version namespace=%s", namespace)
        try:
            _client.set(f"cache-version:{namespace}", "0")
        except redis.RedisError:
            if config.redis_required:
                raise
        return 0
    except redis.RedisError:
        if config.redis_required:
            raise
        return 0


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def consume_if_equals(key: str, expected: str) -> bool:
    """Atomically delete a string key only when its value matches expected."""
    script = """
    local current = redis.call('GET', KEYS[1])
    if not current then return 0 end
    if current ~= ARGV[1] then return 0 end
    redis.call('DEL', KEYS[1])
    return 1
    """
    try:
        return bool(_client.eval(script, 1, key, expected))
    except redis.RedisError:
        logger.exception("Redis atomic consume failure")
        if config.redis_required:
            raise
        return False


def verify_otp_digest(key: str, actual_digest: str, max_attempts: int) -> str:
    """Atomically verify and consume an OTP payload.

    Returns one of: ``ok``, ``missing``, ``invalid`` or ``locked``.
    """
    script = """
    local raw = redis.call('GET', KEYS[1])
    if not raw then return 'missing' end
    local ok, payload = pcall(cjson.decode, raw)
    if not ok then
      redis.call('DEL', KEYS[1])
      return 'missing'
    end
    local attempts = tonumber(payload['attempts'] or 0) + 1
    if attempts > tonumber(ARGV[2]) then
      redis.call('DEL', KEYS[1])
      return 'locked'
    end
    if tostring(payload['digest'] or '') ~= ARGV[1] then
      payload['attempts'] = attempts
      local ttl = redis.call('TTL', KEYS[1])
      if ttl > 0 then
        redis.call('SET', KEYS[1], cjson.encode(payload), 'EX', ttl)
      else
        redis.call('DEL', KEYS[1])
      end
      return 'invalid'
    end
    redis.call('DEL', KEYS[1])
    return 'ok'
    """
    try:
        result = _client.eval(script, 1, key, actual_digest, max_attempts)
        return str(result)
    except redis.RedisError:
        logger.exception("Redis OTP verification failure")
        if config.redis_required:
            raise
        return "missing"


def rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
    """Atomic fixed-window limit.

    Returns ``(allowed, remaining, retry_after_seconds)``. The final value is
    Redis' actual TTL, not merely the configured window, so clients receive an
    accurate ``Retry-After`` header even late in the window.
    """
    script = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
    local remaining = tonumber(ARGV[1]) - current
    if remaining < 0 then remaining = 0 end
    local ttl = redis.call('TTL', KEYS[1])
    if ttl < 1 then
      redis.call('EXPIRE', KEYS[1], ARGV[2])
      ttl = tonumber(ARGV[2])
    end
    if current > tonumber(ARGV[1]) then return {0, remaining, ttl} end
    return {1, remaining, ttl}
    """
    try:
        allowed, remaining, retry_after = _client.eval(
            script, 1, key, limit, window_seconds
        )
        return bool(allowed), int(remaining), max(1, int(retry_after))
    except redis.RedisError:
        logger.exception("Redis rate-limit failure")
        if config.redis_required:
            raise
        return True, limit, 0


def store_refresh_token(user_id: int, jti: str, family: str, ttl: int) -> None:
    """Store refresh state plus per-user and per-family indexes atomically."""
    user_key = f"refresh-user:{user_id}"
    family_key = f"refresh-family:{family}"
    try:
        pipe = _client.pipeline(transaction=True)
        pipe.setex(f"refresh:{jti}", ttl, f"{user_id}:{family}")
        pipe.sadd(user_key, jti)
        pipe.expire(user_key, ttl)
        pipe.sadd(family_key, jti)
        pipe.expire(family_key, ttl)
        pipe.execute()
    except redis.RedisError:
        logger.exception("Redis refresh-token storage failed user_id=%s", user_id)
        if config.redis_required:
            raise

def register_refresh_token(user_id: int, jti: str, ttl: int) -> None:
    """Track refresh JTIs per user so security-sensitive changes can revoke all."""
    key = f"refresh-user:{user_id}"
    try:
        pipe = _client.pipeline(transaction=True)
        pipe.sadd(key, jti)
        pipe.expire(key, ttl)
        pipe.execute()
    except redis.RedisError:
        logger.exception("Redis refresh-token registration failed user_id=%s", user_id)
        if config.redis_required:
            raise


def unregister_refresh_token(user_id: int, jti: str, family: str | None = None) -> None:
    try:
        pipe = _client.pipeline(transaction=True)
        pipe.srem(f"refresh-user:{user_id}", jti)
        if family:
            pipe.srem(f"refresh-family:{family}", jti)
        pipe.execute()
    except redis.RedisError:
        logger.exception("Redis refresh-token unregister failed user_id=%s", user_id)
        if config.redis_required:
            raise


def revoke_refresh_family(family: str) -> int:
    """Revoke a token family using its index, with an old-version fallback."""
    if not family:
        return 0
    removed = 0
    family_key = f"refresh-family:{family}"
    try:
        members = set(_client.smembers(family_key))
        for jti in members:
            value = _client.get(f"refresh:{jti}")
            if value:
                user_id_text = value.split(":", 1)[0]
                removed += int(_client.delete(f"refresh:{jti}"))
                if user_id_text.isdigit():
                    _client.srem(f"refresh-user:{user_id_text}", jti)
        _client.delete(family_key)

        # Compatibility fallback for refresh tokens issued before family sets.
        suffix = f":{family}"
        for candidate in _client.scan_iter("refresh:*"):
            candidate_text = str(candidate)
            if candidate_text.startswith(("refresh-user:", "refresh-family:")):
                continue
            value = _client.get(candidate_text)
            if value and value.endswith(suffix):
                jti = candidate_text.split(":", 1)[1]
                user_id_text = value.split(":", 1)[0]
                removed += int(_client.delete(candidate_text))
                if user_id_text.isdigit():
                    _client.srem(f"refresh-user:{user_id_text}", jti)
        return removed
    except redis.RedisError:
        logger.exception("Redis refresh-family revocation failed family=%s", family)
        if config.redis_required:
            raise
        return removed


def revoke_user_refresh_tokens(user_id: int) -> int:
    """Delete every known refresh token for a user.

    A scan fallback also catches tokens created by older package versions that
    did not maintain the per-user set.
    """
    removed = 0
    set_key = f"refresh-user:{user_id}"
    try:
        members = set(_client.smembers(set_key))
        for jti in members:
            token_key = f"refresh:{jti}"
            value = _client.get(token_key)
            if value:
                _, _, family = value.partition(":")
                if family:
                    _client.srem(f"refresh-family:{family}", jti)
                removed += int(_client.delete(token_key))
        _client.delete(set_key)

        prefix = f"{user_id}:"
        for candidate in _client.scan_iter("refresh:*"):
            candidate_text = str(candidate)
            if candidate_text.startswith(("refresh-user:", "refresh-family:")):
                continue
            value = _client.get(candidate_text)
            if value and value.startswith(prefix):
                jti = candidate_text.split(":", 1)[1]
                _, _, family = value.partition(":")
                if family:
                    _client.srem(f"refresh-family:{family}", jti)
                removed += int(_client.delete(candidate_text))
        return removed
    except redis.RedisError:
        logger.exception("Redis user refresh-token revocation failed user_id=%s", user_id)
        if config.redis_required:
            raise
        return removed
