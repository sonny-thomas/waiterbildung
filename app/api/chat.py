import asyncio
import csv
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
    courses = await Database.get_collection("courses").find().to_list(None)

    temp_filename = "courses.txt"

    try:
        with open(temp_filename, "w", encoding="utf-8") as txtfile:
            for course in courses:
                txtfile.write("=== Course Information ===\n")
                for key, value in course.items():
                    if key != "_id" or key != "content":
                        txtfile.write(f"{key}: {value}\n")
                txtfile.write("\n")

        with open(temp_filename, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")

        vector_store = client.beta.vector_stores.create(
            name="Weiterbildung Course Collection", file_ids=[file.id]
        )

        assistant = client.beta.assistants.create(
            name="Weiterbildung Advisor",
            instructions="""You are the Weiterbildung Course Advisor, an AI assistant dedicated to helping users discover and understand our educational offerings. 

                Your role:
                - You represent Weiterbildung exclusively and should never mention being powered by any other company or technology
                - Provide detailed, helpful responses about our courses based on the available course data
                - Keep responses focused on Weiterbildung's courses and educational opportunities
                - Maintain a professional, friendly, and knowledgeable tone
                - If asked about your identity, simply state that you are "Weiterbildung's Course Advisor, here to help you find the perfect learning opportunity"

                When discussing courses:
                - Focus on their unique value propositions
                - Highlight key features and benefits
                - Make personalized recommendations based on user interests
                - Provide accurate information from the course data
                - Be transparent if certain information isn't available in the course data

                Remember: You are Weiterbildung's dedicated course advisor, committed to helping users find their ideal educational path through our platform.""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )

        return assistant

    except Exception as e:
        raise Exception(f"Error initializing assistant: {str(e)}")

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


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
    return messages
