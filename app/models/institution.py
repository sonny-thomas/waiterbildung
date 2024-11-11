from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class Institution(BaseModel):
    id: str
    name: str
    base_url: HttpUrl
    status: str
    task_id: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    message: Optional[str] = None
    target_fields: list
