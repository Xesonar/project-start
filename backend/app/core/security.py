from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.core.config import settings


class TokenError(Exception):
    pass


def create_access_token(*, subject: int, role: str, expire_days: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(days=expire_days if expire_days is not None else settings.jwt_expire_days)
    payload = {
        "sub": str(subject),
        "role": role,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
