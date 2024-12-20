from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import requests

from app.core import settings
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login/")


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_token(
    data: str, token_type: str = "access", remember_me: bool = False
) -> str:
    """Create a JWT token"""
    to_encode = {"user_id": data, "remember_me": remember_me}
    if token_type == "access":
        exp = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    elif token_type == "refresh":
        if remember_me:
            exp = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        else:
            exp = datetime.now(timezone.utc) + timedelta(days=1)
    else:
        raise ValueError("Invalid token type")
    to_encode.update({"exp": exp, "type": token_type})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> tuple:
    """
    Verify a JWT token and return the user id and expiration time if valid.

    Args:
        token (str): The JWT token.
        token_type (str): The type of the token, either "access" or "refresh".

    Returns:
        tuple: The user id and expiration time if the token is valid.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload.get("user_id"), payload.get("remember_me")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def is_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Check if the token is valid and retrieve the user information.

    Args:
        token (str): The JWT token.

    Returns:
        User: The user information if the token is valid.

    Raises:
        HTTPException: If the token is invalid or user not found.
    """
    user_id, _ = verify_token(token)
    user = await User.get(user_id)
    if user and user.is_active:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def is_admin(user: User = Depends(is_user)) -> User:
    """
    Check if the user associated with the given token is an admin.

    Args:
        user (User): The user object.

    Returns:
        User: The user object if the user is an admin.

    Raises:
        HTTPException: If the user is not an admin.
    """
    if user.role == UserRole.ADMIN:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this resource",
    )


def get_google_user_info(code: str) -> dict:
    """Exchanges google authorization code and retrieves user information."""
    try:
        response = requests.post(
            settings.GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")

        user_info_headers = {"Authorization": f"Bearer {access_token}"}
        user_info_response = requests.get(
            settings.GOOGLE_USERINFO_URL, headers=user_info_headers, timeout=10
        )
        user_info_response.raise_for_status()
        return user_info_response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user information from Google",
        )
