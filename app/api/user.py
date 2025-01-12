from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    """Get a user by ID"""
    user = User.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(**user.model_dump())
