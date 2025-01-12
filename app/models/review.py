from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.models import BaseModel


class Review(BaseModel):
    __tablename__ = "reviews"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)

    user = relationship("User", backref=backref("reviews", lazy="dynamic"))
    course = relationship("Course", backref=backref("reviews", lazy="dynamic"))
