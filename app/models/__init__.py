from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar
from uuid import uuid4

from sqlalchemy import DateTime, String, or_, and_
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base

T = TypeVar("T", bound="BaseModel")


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def model_dump(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def get(cls: type[T], db: Session, **filters: Any) -> T | None:
        query = db.query(cls)
        for attr, value in filters.items():
            if hasattr(cls, attr):
                query = query.filter(getattr(cls, attr) == value)
        return query.first()

    @classmethod
    def get_all(
        cls: type[T],
        db: Session,
        page: int = 1,
        size: int = 100,
        sort_by: Optional[str] = None,
        descending: bool = False,
        use_or: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
    ) -> tuple[List[T], int]:
        skip = (page - 1) * size
        query = db.query(cls)
        conditions = []

        if filters:
            filter_conditions = []
            for attr, value in filters.items():
                if hasattr(cls, attr):
                    filter_conditions.append(getattr(cls, attr) == value)
                else:
                    raise ValueError(f"Invalid filter attribute: {attr}")
            if filter_conditions:
                conditions.append(
                    or_(*filter_conditions)
                    if use_or
                    else and_(*filter_conditions)
                )

        if search:
            search_fields = getattr(cls, "SEARCH_FIELDS", [])
            if search_fields:
                search_conditions = []
                for field in search_fields:
                    if hasattr(cls, field):
                        search_conditions.append(
                            getattr(cls, field).ilike(f"%{search}%")
                        )
                    else:
                        raise ValueError(f"Invalid search field: {field}")
                if search_conditions:
                    conditions.append(or_(*search_conditions))

        if conditions:
            query = query.filter(*conditions)

        total = query.count()

        if sort_by:
            if not hasattr(cls, sort_by):
                raise ValueError(f"Invalid sort attribute: {sort_by}")
            order_attr = getattr(cls, sort_by)
            query = query.order_by(
                order_attr.desc() if descending else order_attr
            )

        data = query.offset(skip).limit(size).all()
        return data, total

    def save(self: T, db: Session) -> T:
        if not self.id:
            db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def delete(self, db: Session) -> bool:
        db.delete(self)
        db.commit()
        return True
