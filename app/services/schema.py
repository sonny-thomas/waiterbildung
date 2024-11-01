import json
import os
from uuid import uuid4
from typing import List
from openai import OpenAI
import asyncio
from app.core.config import logger, settings


async def generate_schema(html_content: str, target_fields: List[str]) -> dict:
    """Generate extraction schema using OpenAI"""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    temp_filename = f"/tmp/{uuid4()}.html"
    try:
        with open(temp_filename, "w+b") as f:
            f.write(html_content.encode("utf-8"))
            f.seek(0)
            file = client.files.create(file=f, purpose="assistants")

        vector_store = client.beta.vector_stores.create(
            name="Schema Analysis", file_ids=[file.id]
        )

        assistant = client.beta.assistants.create(
            name="Schema Generator",
            instructions=f"""You are an expert web scraping analyst. Analyze the HTML structure and generate precise CSS selectors for the target fields: {target_fields}.
            The json schema should follow this structure, and ensure it is always a json structure even nested fields:
            {{
                "fields": [
                    {{
                        "name": "field_name",  # Name of the field to extract (e.g., title, price, description), Mandatory
                        "primary_selector": "CSS selector",  # Mandatory
                        "fallback_selectors": ["alternative1", "alternative2"],  # Optional, if primary selector fails
                        "data_type": "type",
                        "nested_fields": [{{...}}]  # Optional, if the field has nested fields
                    }}
                ]
            }}
            Note: Nested fields are indicated by dot notation in the target fields. For example, 'contact_info.email' should be nested under 'contact_info'.
            Note: If the data is stored in a simple list without good selectors, use a unique identifier for each item instead of the list index, as the list might rotate or items might be missing or added on another page. Never use list index.
            Important: Ensure that all parent selectors are valid and not empty. Each parent selector should have corresponding child selectors if applicable.""",
            model="gpt-4-turbo-preview",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        )

        thread = client.beta.threads.create()
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Generate a json schema for extracting the following fields: {target_fields}",
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=assistant.id
        )

        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run failed with status: {run_status.status}")
            await asyncio.sleep(1)

        messages = client.beta.threads.messages.list(thread_id=thread.id)

        for message in messages.data:
            if message.role == "assistant":
                content = message.content[0].text.value
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        return json.loads(json_match.group())
                    raise Exception("Could not parse schema from response")

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        try:
            client.files.delete(file.id)
            client.beta.vector_stores.delete(vector_store.id)
            client.beta.assistants.delete(assistant.id)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

