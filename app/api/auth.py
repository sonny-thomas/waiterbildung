from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import User, UserAuth, UserLogin, UserRegister, UserRole
from app.services.auth import (
    create_token,
    get_google_user_info,
    hash_password,
    is_user,
    verify_password,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register_user(user: UserRegister) -> UserAuth:
    """Register a new user"""
    if await User.get(email=user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user: User = await User(
        **user.model_dump(),
        hashed_password=hash_password(user.password),
        role=UserRole.USER,
    ).save()

    access_token = create_token(
        data=user.id,
        token_type="access",
    )
    refresh_token = create_token(
        data=user.id,
        token_type="refresh",
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/login")
async def login_user(user: UserLogin) -> UserAuth:
    """Authenticate and login a user"""
    password = user.password
    user = await User.get(email=user.email_or_phone) or await User.get(
        phone=user.email_or_phone
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_token(
        data=user.id,
        token_type="access",
    )
    refresh_token = create_token(
        data=user.id,
        token_type="refresh",
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/login/", include_in_schema=False)
async def login_user_form(form_data: OAuth2PasswordRequestForm = Depends()) -> UserAuth:
    """Authenticate and login a user using OAuth2 form data"""
    return await login_user(
        UserLogin(email_or_phone=form_data.username, password=form_data.password)
    )


@router.post("/google")
async def login_with_google(code: str):
    """Handle Google OAuth"""
    user_info = get_google_user_info(code)
    user = await User.get(email=user_info["email"])
    if not user:
        user = await User(
            first_name=user_info["name"],
            last_name=user_info["family_name"],
            email=user_info["email"],
            avatar=user_info["picture"],
            hashed_password=hash_password(""),
            role=UserRole.USER,
            is_active=True,
        ).save()

    access_token = create_token(
        data=user.id,
        token_type="access",
    )
    refresh_token = create_token(
        data=user.id,
        token_type="refresh",
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/refresh")
async def refresh_token(refresh_token: str) -> UserAuth:
    """Refresh access token"""
    user_id = verify_token(refresh_token, token_type="refresh")
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
    )

    return UserAuth(access_token=access_token, refresh_token=refresh_token, user=user)


@router.get("/session")
async def get_session(user: User = Depends(is_user)) -> User:
    """Get current user session"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )
    return user
