from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

import asyncio

from app.core.config import settings
from app.core.database import Database

store = {}

async def get_chatbot_settings():
    await Database.connect_db()
    chatbot_settings = await Database.get_collection("chatbotsettings_test").find_one()
    await Database.close_db()
    return chatbot_settings
chatbot_settings = asyncio.run(get_chatbot_settings())
questions = chatbot_settings.pop("questionsToAsk")

class ChatService:
    def __init__(self):
        
        llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_CHAT_MODEL, streaming=True)
        # Answer question
        system_prompt = (
            "# Your purpose\n"
            "- Your name is wAlterbidung, and you are an intelligent assistant here to ask/answer for gathering your user's needs for courses\n"
            "- Interact with the customer politely and simply, with a clear and respectful tone.\n"
            "- Never say `I don't know` always provide helpful guidance.\n"
            "- Each dialog must be concise: 1 or 2 sentences per question until the final answer.\n"
            "- Make the conversation simple and easy to understand, avoiding unnecessary complexity.\n"
            "- Don't repeat any question if answer has mentioned already, if user get rid off topic, lead user to the topic and ask same question again\n"
            "# Story of conversation : \n\n"
            "## Must follow the conversation story\n"
            "- Start with Greeting with one of following question\n"
        )
        for idx, question in enumerate(questions, start=1):
            system_prompt += f"Question {idx} - {question}\n"
            
        system_prompt += "\n"
        system_prompt += "- If you gather all answer to above questions from user, You will just respond `DONE` and Summary of User Info"
        print("-"*50)
        print(system_prompt)
        print("-"*50)
        
        qa_prompt  = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        
        self.chain = qa_prompt | llm
      
        self.llm = llm
        self.store = {}
        
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]
        
    def refresh_session(self, session_id: str):
        if session_id not in self.store:
            return "Session ID is not existing"
        else:
            # Delete the session by the ID
            del self.store[session_id]
            return "Successfully Removed"
        
    def get_answer(self, session_id: str, query: str):
        # Initialize RunnableWithMessageHistory
        conversational_chain = RunnableWithMessageHistory(
            self.chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        
        # General Response from invoke
        # result = conversational_chain.invoke({"input": query}, {"session_id": session_id})
        # return result.content
        
        # Streaming Response
        result_stream =  conversational_chain.stream({"input": query}, {"session_id": session_id})

        # Iterate over the stream to get the response  
        for message in result_stream:
            yield message.content
