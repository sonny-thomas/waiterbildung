from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CourseBase(BaseModel):
    title: str
    university: str
    department: Optional[str]
    description: Optional[str]
    credits: Optional[int]
    prerequisites: Optional[List[str]]
    url: str


class CourseCreate(CourseBase):
    pass


class Course(CourseBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScrapingJob(BaseModel):
    id: str
    status: str
    university: str
    created_at: datetime
    completed_at: Optional[datetime]
    total_courses: Optional[int]
    error_message: Optional[str]
