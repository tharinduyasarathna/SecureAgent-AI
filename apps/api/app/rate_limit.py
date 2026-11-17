
import hashlib
import hmac
import logging
from functools import lru_cache

import redis
from fastapi import HTTPException, Request

from apps.api.app.config import get_settings


logger = logging.getLogger(__name__)

# Atomic increment with automatic expiration.
# A counter is created with its expiry in one Redis operation.
RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])

if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])

return {current, ttl}
"""


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()

    return redis.Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )


def get_client_ip(request: Request) -> str:
    """
    Use the directly connected client address.

    Do not trust X-Forwarded-For from arbitrary clients.
    A trusted reverse proxy must be configured separately.
    """
    if request.client is None:
        return "unknown"

    return request.client.host


def protected_identifier(value: str) -> str:
    """
    Hash identifiers before storing them in Redis.
    HMAC prevents straightforward recovery of email
    addresses from predictable hash inputs.
    """
    settings = get_settings()

    return hmac.new(
        settings.jwt_secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def enforce_rate_limit(
    *,
    identifier: str,
    category: str,
    limit: int,
    window_seconds: int,
) -> None:
    if limit < 1 or window_seconds < 1:
        raise ValueError("Invalid rate limit configuration")

    key = (
        f"secureagent:auth:rate-limit:{category}:"
        f"{protected_identifier(identifier)}"
    )

    try:
        client = get_redis_client()

        result = client.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            window_seconds,
        )

        attempts = int(result[0])
        retry_after = max(1, int(result[1]))

    except redis.RedisError:
        logger.exception(
            "Authentication rate limiter unavailable"
        )

        raise HTTPException(
            status_code=503,
            detail="Authentication temporarily unavailable",
            headers={"Retry-After": "5"},
        ) from None

    if attempts > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
            headers={
                "Retry-After": str(retry_after),
            },
        )


def limit_login(
    request: Request,
    email: str,
) -> None:
    client_ip = get_client_ip(request)
    normalized_email = email.strip().lower()

    # Maximum 5 login attempts per IP per minute.
    enforce_rate_limit(
        identifier=client_ip,
        category="login-ip",
        limit=5,
        window_seconds=60,
    )

    # Maximum 10 attempts per account per 15 minutes.
    # This limit applies across different IP addresses.
    enforce_rate_limit(
        identifier=normalized_email,
        category="login-account",
        limit=10,
        window_seconds=900,
    )


def limit_registration(request: Request) -> None:
    client_ip = get_client_ip(request)

    # Maximum 3 registration requests per IP per hour.
    enforce_rate_limit(
        identifier=client_ip,
        category="register-ip",
        limit=3,
        window_seconds=3600,
    )
