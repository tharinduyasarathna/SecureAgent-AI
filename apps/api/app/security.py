
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from apps.api.app.config import get_settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_token(user_id: int) -> str:
    settings = get_settings()

    if user_id <= 0:
        raise ValueError("Invalid user ID")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(
        minutes=settings.token_minutes
    )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> int:
    settings = get_settings()

    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={
            "require": ["sub", "exp"],
        },
    )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError, KeyError):
        raise jwt.InvalidTokenError(
            "Invalid token subject"
        ) from None

    if user_id <= 0:
        raise jwt.InvalidTokenError(
            "Invalid token subject"
        )

    return user_id
