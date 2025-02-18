import json
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from langchain_core.tools import tool
from openai import OpenAI

from app.core.config import settings
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

openai = OpenAI(api_key=settings.OPENAI_API_KEY)
openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    model_kwargs={"response_format": {"type": "json_object"}},
)

text_splitter = RecursiveCharacterTextSplitter()
embeddings = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)

vector_db = PGVector(
    embeddings=embeddings,
    collection_name="vector_db",
    connection=settings.DATABASE_URI,
    use_jsonb=True,
)


@tool("search_courses")
def search_courses(query: str) -> List[dict]:
    """
    Searches courses using vector similarity search.

    Args:
        query: Search query string.

    Returns:
        A list of dictionaries containing course info.
    """
    print(query)
    search_results = vector_db.similarity_search_with_score(query, k=3)
    results = []
    for doc, score in search_results:
        print("Score:", score)
        if score < 0.2:
            results.append(doc.metadata)

    return results


SYSTEM_PROMPT = """ 
    You are a proactive course advisor for our educational institution. Your role is to guide prospective students 
    through finding the right course by asking specific questions. Focus exclusively on course-related inquiries 
    and maintain control of the conversation flow.

    Lead the conversation by systematically gathering information about:
    1. Preferred degree type (Bachelor's, Master's, etc.)
    2. Desired study mode (Full-time, Part-time)
    3. Preferred campus location
    4. Language preferences for instruction
    5. Budget considerations for tuition
    6. Academic interests and career goals

    Only after gathering sufficient information, use the 'search_courses' tool to find matching courses.
    Do not engage in conversations unrelated to course selection or our institution's offerings.
    Do not ever alter the result gotten from the 'search_courses' tool, not even 1 bit. Ensure you only return the
    result as is.

    Your final response must be a JSON object with two keys: 
    `message` (a string response to the user) and `recommended_courses` (a list of course dictionaries).

    The output should be formatted as a JSON instance that conforms to the JSON schema below:
    {{
    "description": "Always use this tool to structure your response to the user.",
    "properties": {{
        "message": {{
            "description": "The main response message to the user",
            "title": "Main Message", 
            "type": "string"
        }},
        "recommended_courses": {{
            "default": [],
            "description": "List of recommended courses from search_courses results",
            "items": {{
                "type": "object",
                "description": "The course object",
                title: "Course",
            }},
            "title": "Recommended Courses",
            "type": "array"
        }}
    }},
    "required": ["message"]
    }}

    Return ONLY the valid JSON object without any additional formatting or commentary.
    """


def create_workflow():
    def call_model(state: MessagesState):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        llm = openai_llm.bind_tools([search_courses], strict=True)
        chain = prompt | llm
        result: AIMessage = chain.invoke({"messages": state["messages"]})
        state["messages"].append(
            AIMessage(content=result.content, tool_calls=result.tool_calls)
        )
        return state

    tool_node = ToolNode([search_courses])

    def should_continue(state: MessagesState):
        """If the last message has a tool call, continue to the tool node; otherwise, finish."""
        last_message = state["messages"][-1]
        return "tools" if last_message.tool_calls else END

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=MemorySaver())


compiled_workflow = create_workflow()


def start_chat():
    """
    Starts a new conversation chat with the default workflow.
    The returned 'send_message' function accepts a string (user message) and returns a dict with:
      - "message": The agent's final response.
      - "recommended_courses": List of course dictionaries (if any).
    """
    checkpointer = MemorySaver()
    chat_id = id(checkpointer)

    def send_message(message: str) -> Dict[str, Any]:
        try:
            response = compiled_workflow.invoke(
                {"messages": [HumanMessage(content=message)]},
                config={"configurable": {"thread_id": chat_id}},
            )
            final_message = response.get("messages", [])[-1]
            try:
                parsed = json.loads(final_message.content)
                return {
                    "message": parsed.get("message", ""),
                    "recommended_courses": parsed.get(
                        "recommended_courses", []
                    ),
                }
            except json.JSONDecodeError:
                return {
                    "message": final_message.content,
                    "recommended_courses": [],
                }
        except Exception as e:
            return {
                "message": f"An unexpected error occurred: {str(e)}",
                "recommended_courses": [],
            }

    return {"chat_id": chat_id, "send_message": send_message}
