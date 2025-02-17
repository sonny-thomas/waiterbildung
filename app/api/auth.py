from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import oauth2_scheme, user_is_active
from app.core.security.google import get_google_user_info
from app.core.security.jwt import (
    generate_tokens,
    regenerate_tokens,
    revoke_token,
)
from app.core.security.password import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePassword,
    ForgotPassword,
    RefreshToken,
    ResetPassword,
    UserLogin,
    UserRegister,
)
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
            status_code=400,
            detail="User with this phone number already exists",
        )
    user = User(**user.model_dump())
    user.password = hash_password(user.password)
    user.send_verification_token()
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/verify-email")
async def verify_email(
    token: str, db: Session = Depends(get_db)
) -> UserResponse:
    """Verify user email using token"""
    user = User.get(db, verification_token=token)
    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid verification token"
        )
    if user.verification_token_expires_at < datetime.now():
        raise HTTPException(
            status_code=400, detail="Verification token has expired"
        )

    user.is_verified = True
    user.verification_token = None
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/resend-verification-email")
async def resend_verification_email(
    email: str, db: Session = Depends(get_db)
) -> UserResponse:
    """Resend verification email to user"""
    user = User.get(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    user.send_verification_token()
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/login")
async def login_user(
    data: UserLogin, db: Session = Depends(get_db)
) -> AuthResponse:
    """Login a user"""
    user = User.get(db, email=data.email)
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )

    if not user.is_verified:
        raise HTTPException(status_code=401, detail="Email not verified")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    auth = generate_tokens(db, user.id)
    return AuthResponse(
        **auth.model_dump(), user=UserResponse(**user.model_dump())
    )


@router.post("/google")
async def login_with_google(
    access_token: str, db: Session = Depends(get_db)
) -> AuthResponse:
    """Login or register a user with Google OAuth"""
    user_info = await get_google_user_info(access_token)

    user = User.get(db, email=user_info["email"])
    if not user:
        user = User(
            email=user_info["email"],
            first_name=user_info["given_name"],
            last_name=user_info["family_name"],
            avatar=user_info["picture"],
            is_verified=True,
            password=hash_password(user_info["sub"]),
        )
        user.save(db)

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")

    auth = generate_tokens(db, user.id)
    return AuthResponse(
        **auth.model_dump(), user=UserResponse(**user.model_dump())
    )


@router.post("/login/oauth2", include_in_schema=False)
async def login_user_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Authenticate and login a user using OAuth2 form data"""
    return await login_user(
        UserLogin(email=form_data.username, password=form_data.password), db
    )


@router.get("/me")
async def get_current_user(
    user: User = Depends(user_is_active),
) -> UserResponse:
    """Get current logged in user"""
    return UserResponse(**user.model_dump())


@router.post("/refresh")
async def refresh_token(
    data: RefreshToken, db: Session = Depends(get_db)
) -> AuthResponse:
    """Refresh access token"""
    user, auth = regenerate_tokens(db, data.refresh_token)
    return AuthResponse(
        **auth.model_dump(), user=UserResponse(**user.model_dump())
    )


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPassword, db: Session = Depends(get_db)
) -> UserResponse:
    """Send password reset token to user's email"""
    user = User.get(db, email=data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.send_password_reset_token()
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/reset-password")
async def reset_password(
    data: ResetPassword, db: Session = Depends(get_db)
) -> UserResponse:
    """Reset user password using token"""
    user = User.get(db, password_reset_token=data.token)
    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid password reset token"
        )
    if user.password_reset_token_expires_at < datetime.now():
        raise HTTPException(
            status_code=400, detail="Password reset token has expired"
        )

    user.password = hash_password(data.new_password)
    user.password_reset_token = None
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/change-password")
async def change_password(
    data: ChangePassword,
    user: User = Depends(user_is_active),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Change user password"""
    if not verify_password(data.current_password, user.password):
        raise HTTPException(status_code=401, detail="Invalid current password")

    user.password = hash_password(data.new_password)
    user.save(db)

    return UserResponse(**user.model_dump())


@router.post("/logout")
async def logout_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> str:
    """Logout a user"""
    revoke_token(db, token)
    return "Successfully logged out"
