from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.middleware import user_is_active, user_is_admin
from app.core.security.password import generate_password, hash_password
from app.models.review import Review
from app.models.user import User
from app.schemas import PaginatedRequest, PaginatedResponse
from app.schemas.course import ReviewResponse
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
    try:
        user_data = user.model_dump()
        user_data["is_verified"] = True
        user_data["password"] = hash_password(generate_password())

        new_user = User(**user_data)
        new_user.save(db)
        return UserResponse(**new_user.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("s")
async def get_all_users(
    pagination: UserPaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
) -> PaginatedResponse[UserResponse]:
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_active),
) -> UserResponse:
    """Get a user by ID"""
    try:
        user = User.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(**user.model_dump())
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user: UserUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
) -> UserResponse:
    """Update user details"""
    try:
        user_to_update = User.get(db, id=user_id)
        if not user_to_update:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            setattr(user_to_update, key, value)
        user_to_update.save(db)
        return UserResponse(**user_to_update.model_dump())
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_admin),
):
    """Delete a user"""
    try:
        user = User.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        User.delete(db, id=user_id)
        return {"message": "User deleted successfully"}
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/reviews")
async def get_user_reviews(
    user_id: str,
    pagination: PaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_active),
) -> PaginatedResponse[ReviewResponse]:
    """Get all reviews by a user"""
    try:
        user = User.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        reviews, total = Review.get_all(
            db,
            page=pagination.page,
            size=pagination.size,
            sort_by=pagination.sort_by,
            descending=pagination.descending,
            user_id=user_id,
        )
        pages = (total + pagination.size - 1) // pagination.size
        review_data = [ReviewResponse(**review.model_dump()) for review in reviews]

        return PaginatedResponse(
            data=review_data,
            total=total,
            page=pagination.page,
            pages=pages,
        )
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/bookmarks")
async def get_user_bookmarks(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(user_is_active),
):
    """Get all courses bookmarked by a user"""
    try:
        user = User.get(db, id=user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user.bookmarked_courses
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
