from collections.abc import Generator
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.security.tokens import ALGORITHM
bearer_scheme = HTTPBearer(auto_error=False)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user