import asyncio
from datetime import datetime
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from app.core.config import settings
from app.core.database import Database
from app.models.chat import ChatData

router = APIRouter(tags=["chatbot"])

client = OpenAI(api_key=settings.OPENAI_API_KEY)
async def initialize_assistant():
    await Database.connect_db()
    courses = await Database.get_collection("courses").find().to_list()
    temp_filename = "courses.json"
    try:
        with open(temp_filename, "wb") as f:
            import json
            from bson import ObjectId

            def convert_objectid(obj):
                if isinstance(obj, ObjectId):
                    return
                elif isinstance(obj, datetime):
                    return
                raise TypeError("Object of type %s is not JSON serializable" % type(obj).__name__)

            json_data = json.dumps(courses, default=convert_objectid)
            f.write(json_data.encode('utf-8'))
            f.seek(0)
            file = client.files.create(file=f, purpose="assistants")

        vector_store = client.beta.vector_stores.create(
            name="Course Collection", file_ids=[file.id]
        )

        assistant = client.beta.assistants.create(
            name="Course Advisor",
            instructions="",
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )
    finally:
        pass
        # if os.path.exists(temp_filename):
        #     os.remove(temp_filename)
    return assistant

assistant = asyncio.run(initialize_assistant())


@router.post("/start_thread")
async def start_thread():
    """Endpoint to start a new thread."""
    try:
        thread = client.beta.threads.create()
        return {"thread_id": thread.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(chat: ChatData):
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
            raise Exception(f"Run failed with status: {run_status.status}")
        await asyncio.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=chat.thread_id)
    return {"message": messages.data[0].content[0].text.value}
    
