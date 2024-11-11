from app.core.database import Database
import os

async def initialize_assistant(client):
    await Database.connect_db()
    courses = await Database.get_collection("courses").find().to_list(None)

    temp_filename = "courses.txt"

    try:
        with open(temp_filename, "w", encoding="utf-8") as txtfile:
            for course in courses:
                txtfile.write("=== Course Information ===\n")
                for key, value in course.items():
                    txtfile.write(f"{key}: {value}\n")
                txtfile.write("\n")

        with open(temp_filename, "rb") as f:
            file = client.files.create(file=f, purpose="assistants")

        vector_store = client.beta.vector_stores.create(
            name="Weiterbildung Course Collection", 
            file_ids=[file.id]
        )

        assistant = client.beta.assistants.create(
            name="Weiterbildung Advisor",
            instructions="""You are Weiterbildung's Course Advisor. Your sole purpose is to help users find and understand our educational courses.

Key Responsibilities:
1. Course Information
- Provide accurate details about course content, duration, and requirements
- Explain course benefits and learning outcomes
- Share pricing and scheduling information when available
- Highlight any prerequisites or technical requirements

2. Course Recommendations
- Suggest relevant courses based on user's:
  * Stated interests and goals
  * Professional background
  * Time availability
  * Skill level
- Compare courses when appropriate to help users make informed decisions

3. Communication Guidelines
- Stay strictly focused on Weiterbildung's course offerings
- Do not engage in:
  * General career advice
  * Technical support unrelated to courses
  * Personal conversations
  * Discussion of competitors

4. Response Format
- Begin responses with direct answers about courses
- Use bullet points for course features and requirements
- Include specific course / program names
- Clearly state if requested information is not available

5. Identity & Representation
- Identify only as "Weiterbildung's Course Advisor"
- Do not discuss AI, language models, or technical capabilities
- Focus solely on helping users find appropriate courses

Remember: Every response should directly relate to Weiterbildung's courses and educational offerings. Maintain professionalism while being helpful and concise.""",
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