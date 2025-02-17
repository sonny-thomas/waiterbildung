from app.core.config import settings
import requests
from fastapi import HTTPException, status


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

        user_info_response = requests.get(
            settings.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        user_info_response.raise_for_status()
        return user_info_response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user information from Google",
        )
