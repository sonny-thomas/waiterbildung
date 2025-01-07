from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import (
    Email,
    ResetPassword,
    Token,
    User,
    UserAuth,
    UserLogin,
    UserRegister,
    UserRole,
    EmailVerification,
    PasswordReset,
)
from app.services.auth import (
    create_token,
    get_google_user_info,
    hash_password,
    is_user,
    verify_password,
    verify_token,
)
from app.services.email import (
    send_email_verified,
    send_verification_email,
    send_welcome_email,
    send_password_reset_success,
    send_password_reset_request,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register_user(user: UserRegister) -> dict:
    """Register a new user"""
    if await User.get(email=user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered, login to continue",
        )
    user: User = await User(
        **user.model_dump(),
        hashed_password=hash_password(user.password),
        is_active=True,
        role=UserRole.USER,
    ).save()
    verification: EmailVerification = await EmailVerification(id=user.id).save()
    send_welcome_email(user.email, user.first_name, verification.token)

    return {
        "message": "User registered successfully, check your inbox for a verification email"
    }


@router.post("/verify-email")
async def verify_email(request: Token) -> dict:
    """Verify user's email"""
    verification: EmailVerification = await EmailVerification.get(token=request.token)

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token, request a new one",
        )

    verification_time = verification.updated_at
    if (datetime.now(timezone.utc) - verification_time).total_seconds() > 86400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification] token expired, request a new one",
        )

    user: User = await User.get(id=verification.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found, request a new verification email",
        )
    user.is_verified = True
    await user.save()

    await verification.save()
    send_email_verified(user.email, user.first_name)

    return {"message": "Email verified successfully"}


@router.post("/resend-verification-email")
async def resend_verification_email(request: Email) -> dict:
    """Resend verification email"""
    user: User = await User.get(email=request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found, register a new account",
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified, login to continue",
        )

    verification = await EmailVerification(id=user.id).save()
    send_verification_email(user.email, user.first_name, verification.token)
    return {"message": "Verification email resent successfully"}


@router.post("/login")
async def login_user(user: UserLogin) -> UserAuth:
    """Authenticate and login a user"""
    password = user.password
    remember_me = user.remember_me
    user: User = await User.get(email=user.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified, check your inbox for a verification email",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive, contact support",
        )

    access_token = create_token(
        data=user.id,
        token_type="access",
    )
    refresh_token = create_token(
        data=user.id, token_type="refresh", remember_me=remember_me
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/login/", include_in_schema=False)
async def login_user_form(form_data: OAuth2PasswordRequestForm = Depends()) -> UserAuth:
    """Authenticate and login a user using OAuth2 form data"""
    return await login_user(
        UserLogin(email=form_data.username, password=form_data.password)
    )


@router.post("/google")
async def login_with_google(request: Token) -> UserAuth:
    """Handle Google OAuth"""
    user_info = get_google_user_info(request.token)
    user: User = await User.get(email=user_info["email"])

    if not user:
        user = await User(
            first_name=user_info["name"],
            last_name=user_info["family_name"],
            email=user_info["email"],
            avatar=user_info["picture"],
            hashed_password=hash_password(""),
            role=UserRole.USER,
            is_verified=True,
        ).save()
        send_welcome_email(user.email, user.first_name)

    if not user.avatar or not user.is_verified:
        user.avatar = user_info["picture"]
        user.is_verified = True
        await user.save()

    access_token = create_token(
        data=user.id,
        token_type="access",
    )
    refresh_token = create_token(
        data=user.id,
        token_type="refresh",
        remember_me=True,
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/refresh")
async def refresh_token(request: Token) -> UserAuth:
    """Refresh access token"""
    user_id, remember_me = verify_token(request.token, token_type="refresh")
    user = await User.get(id=user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    access_token = create_token(
        data=user.id,
        token_type="access",
    )
    refresh_token = create_token(
        data=user.id,
        token_type="refresh",
        remember_me=remember_me,
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.get("/me")
async def get_me(user: User = Depends(is_user)) -> User:
    """Get current user"""
    return user


@router.post("/forgot-password")
async def forgot_password(request: Email) -> dict:
    """Send password reset link"""
    user = await User.get(email=request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    password_reset: PasswordReset = await PasswordReset(id=user.id).save()
    send_password_reset_request(user.email, user.first_name, password_reset.token)
    return {"message": "Password reset link sent successfully"}


@router.post("/reset-password")
async def reset_password(request: ResetPassword) -> dict:
    """Reset user password"""
    if request.old_password:
        user: User = await is_user()
        if not verify_password(request.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid old password",
            )
    elif request.token:
        password_reset = await PasswordReset.get(token=request.token)
        if not password_reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )
        if (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(password_reset.updated_at)
        ).total_seconds() > 86400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expired, request a new one",
            )
        user: User = await User.get(id=password_reset.id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        await password_reset.save()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either old_password or token must be provided",
        )

    user.hashed_password = hash_password(request.new_password)
    await user.save()
    send_password_reset_success(user.email, user.first_name)
    return {"message": "Password reset successfully"}
