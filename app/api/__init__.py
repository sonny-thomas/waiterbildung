from fastapi import APIRouter

from app.api import auth, course, institution

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(institution.router)
api_router.include_router(course.router)
