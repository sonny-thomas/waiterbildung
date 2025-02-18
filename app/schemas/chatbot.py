from pydantic import BaseModel
from typing import List, Any


class MessageRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    chat_id: str
    message: str
    recommended_courses: List[Any]
