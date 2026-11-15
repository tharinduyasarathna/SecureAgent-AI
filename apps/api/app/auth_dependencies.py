
import jwt

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from apps.api.app.database import get_db
from apps.api.app.models import User
from apps.api.app.security import decode_token

bearer = HTTPBearer()


def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = decode_token(auth.credentials)
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        ) from None

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    return user
