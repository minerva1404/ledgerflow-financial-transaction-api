from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> UUID:
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        options={"require": ["sub", "exp"]},
    )
    return UUID(payload["sub"])