from pydantic import BaseModel

class ChatMessage(BaseModel):
    isBot: bool
    text: str

class ChatData(BaseModel):
    thread_id: str
    message: str