from fastapi import APIRouter

from app.api import auth, institution, user

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(institution.router)
