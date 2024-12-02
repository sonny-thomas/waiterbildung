from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from app.models.user import User, UserRole
from app.services.auth import is_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    first_name: Optional[str] = Query(None),
    last_name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(is_user),
) -> List[User]:
    """
    List users with optional filtering and pagination

    - Supports pagination
    - Optional filtering by:
      * first_name (partial match)
      * last_name (partial match)
      * email (partial match)
      * phone (partial match)
      * role
      * is_active status
    - Returns list of serialized users
    """
    filters = {
        "first_name": {"$regex": first_name, "$options": "i"} if first_name else None,
        "last_name": {"$regex": last_name, "$options": "i"} if last_name else None,
        "email": {"$regex": email, "$options": "i"} if email else None,
        "phone": {"$regex": phone, "$options": "i"} if phone else None,
        "role": role.value if role else None,
        "is_active": is_active if is_active is not None else None,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    try:
        return await User.list(page=page, limit=limit, filters=filters)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    _: User = Depends(is_user),
) -> User:
    """
    Retrieve a specific user by ID

    - Returns 404 if user not found
    """
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
