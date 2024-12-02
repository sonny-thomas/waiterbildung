import requests
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import User, UserAuth, UserLogin, UserRegister, UserRole
from app.services.auth import (
    create_token,
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


@router.get("/callback/google")
async def google_callback(code: str):
    """Handle Google OAuth2 callback"""
    # Exchange the authorization code for an access token
    token_response = await exchange_code_for_token(code)
    id_token = token_response.get("id_token")
    access_token = token_response.get("access_token")

    # Verify the ID token
    user_info = await verify_google_id_token(id_token)

    # Check if user already exists
    user = await User.get(email=user_info["email"])
    if not user:
        # Register new user
        user = await User(
            email=user_info["email"],
            hashed_password=hash_password(""),  # No password for OAuth users
            role=UserRole.USER,
            is_active=True,
        ).save()

    # Create tokens
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

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_CLIENT_ID = (
    "390071238326-kih70pkv4u5t44tn8s1mikkveugpmcd1.apps.googleusercontent.com"
)
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_REDIRECT_URI = "http://localhost:3000"


def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token"""

    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            json={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code for token: {e}",
        )


def verify_google_id_token(id_token: str) -> dict:
    """Verify Google ID token and return user info"""
    response = requests.get(
        GOOGLE_USERINFO_URL,
        params={"id_token": id_token},
    )
    response.raise_for_status()
    return response.json()
