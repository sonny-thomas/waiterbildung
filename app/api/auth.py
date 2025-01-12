from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import oauth2_scheme
from app.core.security.jwt import generate_tokens, regenerate_tokens, revoke_token
from app.core.security.password import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, RefreshTokenRequest, UserLogin, UserRegister
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register_user(
    user: UserRegister, db: Session = Depends(get_db)
) -> UserResponse:
    """Register a new user"""
    if User.get(db, email=user.email):
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )
    if User.get(db, phone=user.phone):
        raise HTTPException(
            status_code=400, detail="User with this phone number already exists"
        )
    user = User(**user.model_dump())
    user.password = hash_password(user.password)
    user.send_verification_token()
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/login")
async def login_user(data: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    """Login a user"""
    user = User.get(db, email=data.email)
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=401, detail="Email not verified")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    auth = generate_tokens(db, user.id)
    return AuthResponse(**auth.model_dump(), user=UserResponse(**user.model_dump()))


@router.post("/login/oauth2", include_in_schema=False)
async def login_user_form(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> AuthResponse:
    """Authenticate and login a user using OAuth2 form data"""
    return await login_user(
        UserLogin(email=form_data.username, password=form_data.password), db
    )


@router.post("/refresh")
async def refresh_token(
    data: RefreshTokenRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    """Refresh access token"""
    user, auth = regenerate_tokens(db, data.refresh_token)
    return AuthResponse(**auth.model_dump(), user=UserResponse(**user.model_dump()))


@router.post("/logout")
async def logout_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)
) -> str:
    """Logout a user"""
    revoke_token(db, token)
    return "Successfully logged out"
