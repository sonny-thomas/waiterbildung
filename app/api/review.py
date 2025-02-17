from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.middleware import user_is_active
from app.models.review import Review
from app.models.user import User
from app.schemas import PaginatedResponse
from app.schemas.course import (
    ReviewRequest,
    ReviewResponse,
    ReviewPaginatedRequest,
)

router = APIRouter(prefix="/review", tags=["review"])


@router.post("")
async def create_review(
    course_id: str,
    review: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_is_active),
) -> ReviewResponse:
    """Create a new review for a course"""
    try:
        review_data = review.model_dump()
        review_data["course_id"] = course_id
        review_data["user_id"] = current_user.id

        new_review = Review(**review_data)
        new_review.save(db)
        return ReviewResponse(**new_review.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("s")
async def get_all_reviews(
    pagination: ReviewPaginatedRequest = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(user_is_active),
) -> PaginatedResponse[ReviewResponse]:
    """List all reviews with pagination"""
    try:
        filters = {}
        if pagination.user_id:
            filters["user_id"] = pagination.user_id
        if pagination.course_id:
            filters["course_id"] = pagination.course_id

        reviews, total = Review.get_all(
            db,
            page=pagination.page,
            size=pagination.size,
            sort_by=pagination.sort_by,
            descending=pagination.descending,
            **filters
        )
        pages = (total + pagination.size - 1) // pagination.size
        review_data = [
            ReviewResponse(**review.model_dump()) for review in reviews
        ]

        return PaginatedResponse(
            data=review_data,
            total=total,
            page=pagination.page,
            pages=pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{review_id}")
async def get_review_by_id(
    review_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(user_is_active),
) -> ReviewResponse:
    """Get a review by ID"""
    try:
        review = Review.get(db, id=review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        return ReviewResponse(**review.model_dump())
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{review_id}")
async def update_review(
    review_id: str,
    review: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_is_active),
) -> ReviewResponse:
    """Update a review"""
    try:
        existing_review = Review.get(db, id=review_id)
        if not existing_review:
            raise HTTPException(status_code=404, detail="Review not found")

        if existing_review.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this review"
            )
        update_data = review.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_review, key, value)
        existing_review.save(db)
        return ReviewResponse(**existing_review.model_dump())
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(user_is_active),
):
    """Delete a review"""
    try:
        existing_review = Review.get(db, id=review_id)
        if not existing_review:
            raise HTTPException(status_code=404, detail="Review not found")

        if existing_review.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this review"
            )

        Review.delete(db, id=review_id)
        return {"message": "Review deleted successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
