import asyncio

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from app.core.config import settings
from app.models.chat import ChatRequest
from app.services.chat import initialize_assistant

router = APIRouter(tags=["chatbot"], prefix="")

client = OpenAI(api_key=settings.OPENAI_API_KEY)
assistant = asyncio.run(initialize_assistant(client))


@router.post("/start_thread")
async def start_thread() -> dict:
    """Endpoint to start a new thread."""
    try:
        thread = client.beta.threads.create()
        return {"thread_id": thread.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(chat: ChatRequest) -> str:
    """Endpoint to handle chat requests."""

    client.beta.threads.messages.create(
        thread_id=chat.thread_id,
        role="user",
        content=chat.message,
    )

    run = client.beta.threads.runs.create(
        thread_id=chat.thread_id, assistant_id=assistant.id
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=chat.thread_id, run_id=run.id
        )
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            raise HTTPException(status_code=500, detail=str(run_status))
        await asyncio.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=chat.thread_id)
    return messages.data[0].content[0].text.value
