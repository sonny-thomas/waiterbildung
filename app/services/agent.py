import time
import threading

from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

from app.core.config import settings
from app.core.database import Database

store = {}


class ChatService:
    async def initialize(self):
        llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_CHAT_MODEL,
            streaming=True,
        )
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
        try:
            chatbot_settings = await Database.get_collection(
                "chatbotsettings_test"
            ).find_one()
        except Exception as e:
            print(f"Error fetching chatbot settings: {e}")
            chatbot_settings = None

        questions = (
            chatbot_settings.get("questionsToAsk", []) if chatbot_settings else []
        )

        for idx, question in enumerate(questions, start=1):
            system_prompt += f"Question {idx} - {question}\n"

        system_prompt += "\n"
        system_prompt += "- If you gather all answer to above questions from user, You will just respond `DONE` and conversation summary\n"

        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        self.chain = qa_prompt | llm

        self.llm = llm
        self.store = {}

        # Session Expiry and Check Interval
        self.session_expiry = 30 * 60  # 30 minutes in seconds
        self.check_interval = 60  # 1 min
        self.lock = threading.Lock()
        self._start_session_cleaner()

    # Session Cleaner function
    def _start_session_cleaner(self):
        def clean_sessions():
            while True:
                current_time = time.time()
                print(f"Cleaning session function called {current_time} ", flush=True)
                expired_sessions = [
                    session_id
                    for session_id, session_data in self.store.items()
                    if current_time - session_data["last_active"] > self.session_expiry
                ]

                for session_id in expired_sessions:
                    with self.lock:  # Acquire the lock before deleting from `store`
                        if session_id in self.store:
                            print(
                                f"Deleted Session: {self.store[session_id]}", flush=True
                            )
                            del self.store[session_id]
                        else:
                            print(
                                f"Session ID {session_id} not found during cleanup.",
                                flush=True,
                            )

                time.sleep(self.check_interval)  # Check every minute

        cleaner_thread = threading.Thread(target=clean_sessions, daemon=True)
        cleaner_thread.start()

    def get_all_session_history(self):
        return self.store

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = {
                "history": ChatMessageHistory(),
                "last_active": time.time(),
            }
        else:
            # Update the last active time
            self.store[session_id]["last_active"] = time.time()

        # print("Session History",self.store[session_id])
        return self.store[session_id]["history"]

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
            lambda sid: self.get_session_history(sid),
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        # General Response from invoke
        # result = conversational_chain.invoke({"input": query}, {"session_id": session_id})
        # return result.content

        # Streaming Response
        result_stream = conversational_chain.stream(
            {"input": query}, {"session_id": session_id}
        )

        # Iterate over the stream to get the response
        for message in result_stream:
            yield message.content


client = ChatService()
