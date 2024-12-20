from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import WebBaseLoader
from app.core import settings
from app.models.course import Course

OPENAI_API_KEY = settings.OPENAI_API_KEY
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# Enable structured output from the LLM
structured_llm = llm.with_structured_output(Course)

# Prepare the prompt with context                   
prompt_template = """
Your task is to output the following in a structured format strictly:
- If you can't find some info, include an empty string or a null object.
- Ensure the output is only in English.
- The 'degree' field can only include 'Bachelor', 'Master', 'PhD', or 'None'.
- Don't provide any online course or generate by yourself.
- Provide course date based on following context only.

# Context
{context}
"""

async def generate_course(course_url : str) -> Course:
    loader = WebBaseLoader(course_url)
    docs = loader.load()

    if not docs:
        raise ValueError(f"No content found at URL: {course_url}")

    prompt = prompt_template.format(context=docs[0].page_content)
    result = structured_llm.invoke(prompt)
    return result
