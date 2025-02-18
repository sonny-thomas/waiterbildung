from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.core.chatbot import start_chat
from app.schemas.chatbot import ChatResponse, MessageRequest

router = APIRouter(prefix="/chat", tags=["chatbot"])

chats: Dict[str, Any] = {}


@router.post("/start", response_model=ChatResponse)
async def create_chat():
    """Start a new chat chat"""
    chat = start_chat()
    chat_id = str(chat["chat_id"])
    chats[chat_id] = chat["send_message"]

    intro_response = chat["send_message"]("Hello, how are you")

    return ChatResponse(
        message=intro_response["message"],
        recommended_courses=intro_response["recommended_courses"],
        chat_id=chat_id,
    )


@router.post("/chat/{chat_id}/message", response_model=ChatResponse)
async def send_message(chat_id: str, request: MessageRequest):
    """Send a message in an existing chat"""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="chat not found")

    response = chats[chat_id](request.message)

    return ChatResponse(
        message=response["message"],
        recommended_courses=response["recommended_courses"],
        chat_id=chat_id,
    )
