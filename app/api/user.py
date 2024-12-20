from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.user import User, UserList, UserRole, Status
from app.services.auth import is_user, is_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model_by_alias=False)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("asc"),
    _: User = Depends(is_user),
) -> UserList:
    """
    List users with optional filtering and pagination

    - Supports pagination
    - Optional filtering by:
      * search (partial match on first_name, last_name, email, phone, or full name)
      * role
      * is_active status
      * is_verified status
    - Optional sorting by a field in ascending or descending order
    - Returns list of serialized users
    """
    filters = {}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        filters["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"email": search_regex},
            {"phone": search_regex},
            {
                "$expr": {
                    "$regexMatch": {
                        "input": {"$concat": ["$first_name", " ", "$last_name"]},
                        "regex": search,
                        "options": "i",
                    }
                }
            },
            {
                "$expr": {
                    "$regexMatch": {
                        "input": {"$concat": ["$last_name", " ", "$first_name"]},
                        "regex": search,
                        "options": "i",
                    }
                }
            },
        ]
    if role:
        filters["role"] = role.value
    if is_active is not None:
        filters["is_active"] = is_active
    if is_verified is not None:
        filters["is_verified"] = is_verified

    sort_order = 1 if sort_order == "asc" else -1
    sort = [(sort_by, sort_order)]

    try:
        users, total = await User.list(
            page=page, limit=size, filters=filters, sort=sort
        )
        return UserList(users=users, total=total, page=page, size=size)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}", response_model_by_alias=False)
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


@router.put("/{user_id}", response_model_by_alias=False)
async def update_user(
    user_id: str,
    user: dict,
    _: User = Depends(is_admin),
) -> User:
    """
    Update a user by ID

    - Requires admin privileges
    - Returns 404 if user not found
    - Returns the updated user
    """
    _user = await User.get(user_id)
    if not _user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.items():
        setattr(_user, key, value)
    await _user.save()
    return _user


@router.patch("/{user_id}/status", response_model_by_alias=False)
async def update_user_status(
    user_id: str,
    request: Status,
    _=Depends(is_admin),
) -> User:
    """
    Update a user's active status by ID

    - Returns 404 if user not found
    - Returns the updated user
    """
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = request.is_active
    await user.save()
    return user
