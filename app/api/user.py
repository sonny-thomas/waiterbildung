from app.core.security.password import generate_password, hash_password
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_active, user_is_admin
from app.models.user import User
from app.schemas import PaginatedResponse
from app.schemas.user import (
    UserCreate,
    UserPaginatedRequest,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.post("")
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
) -> UserResponse:
    """Create a new user"""
    user_data = user.model_dump()
    user_data["is_verified"] = True
    user_data["password"] = hash_password(generate_password())

    new_user = User(**user_data)
    new_user.save(db)
    return UserResponse(**new_user.model_dump())


@router.get("s")
async def get_all_users(
    pagination: UserPaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
) -> PaginatedResponse[UserResponse]:
    filters = {}
    if pagination.role:
        filters["role"] = pagination.role
    if pagination.is_active is not None:
        filters["is_active"] = pagination.is_active
    if pagination.is_verified is not None:
        filters["is_verified"] = pagination.is_verified

    users, total = User.get_all(
        db,
        page=pagination.page,
        size=pagination.size,
        sort_by=pagination.sort_by,
        descending=pagination.descending,
        use_or=pagination.use_or,
        filters=filters,
        search=pagination.search,
    )
    pages = (total + pagination.size - 1) // pagination.size
    user_data = [UserResponse(**user.model_dump()) for user in users]

    return PaginatedResponse(
        data=user_data,
        total=total,
        page=pagination.page,
        pages=pages,
    )


@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_active),
) -> UserResponse:
    """Get a user by ID"""
    user = User.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(**user.model_dump())


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user: UserUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
) -> UserResponse:
    """Update user details"""
    user = User.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = User.update(db, user_id, user.model_dump())
    return UserResponse(**updated_user.model_dump())


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
):
    """Delete a user"""
    user = User.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    User.delete(db, id=user_id)
    return {"message": "User deleted successfully"}
