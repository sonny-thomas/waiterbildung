from uuid import uuid4

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.database import Database
from app.models.chat import ChatRequest
from app.services.chat import initialize_assistant

from app.services.chat_new import insert_vector_embedding, remove_embedding_field, create_vector_index, get_relevant_courses
from app.services.utils import generate_embedding_openai
from app.services.agent import client

router = APIRouter(tags=["chatbot"], prefix="")


@router.post("/test/embedding")
async def test_embedding(text: str) -> dict:
    """Endpoint to test OpenAI embedding."""
    embedding = await generate_embedding_openai(text)
    print(embedding)
    return {"embedding": embedding}


@router.get("/embedding/store")
async def store_embedding():
    """Endpoint to store OpenAI embedding."""
    response = await insert_vector_embedding()
    return response

@router.get("/embedding/remove")
async def remove_embedding():
    response = await remove_embedding_field()
    return response

@router.get("/index/create_index")
async def create_index():
    response = await create_vector_index()
    return response
@router.get("/index/search_from_index")
async def search_from_index(query: str):
    response = await get_relevant_courses(query)
    return response

@router.get("/chat/create_session")
async def create_session():
    """Endpoint to create a new chat session."""
    return {"session_id": str(uuid4())}

@router.get("/chat/refresh_session")
async def refresh_session(session_id: str):
    """Endpoint to refresh a chat session."""
    client.refresh_session(session_id)
    return {"session_id": session_id}

@router.get("/chat/get_all_session_history")
async def get_all_session_history():
    """Endpoint to get chat session history."""
    return client.get_all_session_history()


@router.post("/chat")
async def chat(chat: ChatRequest):
    """Endpoint to handle chat requests."""
    session_id = chat.session_id
    message = chat.message
    
    return StreamingResponse(client.get_answer(session_id, message), media_type="text/plain")

@router.get("/chat/settings")
async def chat_settings():
    """Endpoint to get chat settings."""
    print("sdfdsf")
    settings = await Database.get_collection("chatbotsettings").find_one()
    questions = settings.pop("questionsToAsk")
    return questions

@router.post("/start_thread")
async def start_thread() -> dict:
    """Endpoint to start a new thread."""
    return {"thread_id": "1234"}
    # try:
    #     thread = client.beta.threads.create()
    #     return {"thread_id": thread.id}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

# @router.post("/chat")
# async def chat(chat: ChatRequest):
#     """Endpoint to handle chat requests."""

    # client.beta.threads.messages.create(
    #     thread_id=chat.thread_id,
    #     role="user",
    #     content=chat.message,
    # )

    # run = client.beta.threads.runs.create(
    #     thread_id=chat.thread_id, assistant_id=assistant.id
    # )

    # while True:
    #     run_status = client.beta.threads.runs.retrieve(
    #         thread_id=chat.thread_id, run_id=run.id
    #     )
    #     if run_status.status == "completed":
    #         break
    #     elif run_status.status in ["failed", "cancelled", "expired"]:
    #         raise HTTPException(status_code=500, detail=str(run_status))
    #     await asyncio.sleep(1)

    # messages = client.beta.threads.messages.list(thread_id=chat.thread_id)
    # response = messages.data[0].content[0].text.value
    # source_tag_pattern = r'【\d+†source】'
    # response = re.sub(source_tag_pattern, '', response)
    
    response = "Hello, World!"
    return response
