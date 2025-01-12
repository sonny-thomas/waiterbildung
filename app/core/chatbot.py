from openai import OpenAI

from app.core.config import settings

openai = OpenAI(api_key=settings.OPENAI_API_KEY)
