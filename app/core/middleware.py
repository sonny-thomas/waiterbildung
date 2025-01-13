from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security.jwt import verify_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login/oauth2")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    return verify_token(db, token)


async def user_is_active(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")
    return current_user


async def user_is_instructor(
    current_user: Annotated[User, Depends(user_is_active)],
) -> User:
    if current_user.role not in [UserRole.instructor, UserRole.admin]:
        raise HTTPException(
            status_code=403, detail="Only instructors and admins have access"
        )
    return current_user


async def user_is_admin(current_user: Annotated[User, Depends(user_is_active)]) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins have access")
    return current_user
