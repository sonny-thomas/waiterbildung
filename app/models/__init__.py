from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import uuid4

from sqlalchemy import DateTime, String, or_
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
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        descending: bool = False,
        use_or: bool = True,
        **filters: Any,
    ) -> list["BaseModel"]:
        query = db.query(cls)

        if filters:
            filter_conditions = []
            for attr, value in filters.items():
                if hasattr(cls, attr):
                    filter_conditions.append(getattr(cls, attr) == value)
                else:
                    raise ValueError(f"Invalid filter attribute: {attr}")

            if use_or:
                query = query.filter(or_(*filter_conditions))
            else:
                for condition in filter_conditions:
                    query = query.filter(condition)

        if sort_by:
            if not hasattr(cls, sort_by):
                raise ValueError(f"Invalid sort attribute: {sort_by}")
            order_attr = getattr(cls, sort_by)
            query = query.order_by(order_attr.desc() if descending else order_attr)

        query = query.offset(skip).limit(limit)
        return query.all()

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
