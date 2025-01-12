from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.session import Session as AuthSession
from app.models.user import User
from app.schemas.auth import Auth


class TokenData(BaseModel):
    user_id: str
    exp: datetime
    token_type: str


def create_token(user_id: str, token_type: str = "access") -> str:
    """Create a new JWT token"""
    expire = datetime.now(timezone.utc) + (
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        if token_type == "access"
        else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    token_data = TokenData(user_id=user_id, exp=expire, token_type=token_type)
    return str(
        jwt.encode(token_data.model_dump(), settings.SECRET_KEY, algorithm="HS256")
    )


def verify_token(db: Session, token: str, token_type: str = "access") -> User:
    """Verify token and return user_id if valid"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload["token_type"] != token_type:
            raise HTTPException(status_code=401, detail=f"Invalid {token_type} token")
        user = User.get(db, id=payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_tokens(db: Session, user_id: str) -> Auth:
    """Generate new access and refresh tokens"""
    access_token = create_token(user_id, "access")
    refresh_token = create_token(user_id, "refresh")

    auth = AuthSession(
        access_token=access_token, refresh_token=refresh_token, user_id=user_id
    )
    auth.save(db)

    return Auth(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=int(
            (
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            ).timestamp()
        ),
        refresh_token_expires_at=int(
            (
                datetime.now(timezone.utc)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            ).timestamp()
        ),
    )


def regenerate_tokens(db: Session, refresh_token: str) -> tuple[User, Auth]:
    """Regenerate tokens using refresh token"""
    user = verify_token(db, refresh_token, "refresh")

    if user.is_active is False:
        raise HTTPException(status_code=401, detail="Inactive user")

    auth = AuthSession.get(db, refresh_token=refresh_token, user_id=user.id)
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_token(user.id, "access")
    refresh_token = create_token(user.id, "refresh")

    auth.access_token = access_token
    auth.refresh_token = refresh_token
    auth.save(db)

    auth_response = Auth(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=int(
            (
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            ).timestamp()
        ),
        refresh_token_expires_at=int(
            (
                datetime.now(timezone.utc)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            ).timestamp()
        ),
    )

    return user, auth_response


def revoke_token(db: Session, token: str) -> None:
    """Revoke token"""
    user = verify_token(db, token)
    auth = AuthSession.get(db, access_token=token, user_id=user.id)
    if auth:
        auth.delete(db)
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
