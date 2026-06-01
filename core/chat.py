# ============================================================
# YOUR LANGCHAIN CHAIN GOES HERE
# ============================================================
# This stub keeps the app running while you build the chain.
#
# chat_history is a list of dicts from SQLite:
#   [{"role": "human", "content": "..."}, {"role": "ai", "content": "..."}, ...]
#
# Replace get_response() with your LangChain implementation.
# ============================================================


import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def get_response(user_message: str, course_name: str, course_prompt: str, chat_history: list) -> str:
    lc_history = []
    for message in chat_history:
        if message["role"] == "human":
            lc_history.append(HumanMessage(content=message["content"]))
        elif message["role"] == "ai":
            lc_history.append(AIMessage(content=message["content"]))
    teaching_philosophy = """
    For academic questions:
    1. Repeat full question
    2. Professor explanation
    3. Beginner explanation
    4. Analogy
    5. Theory and concepts
    6. Worked examples
    7. Common mistakes
    8. Practice questions
    9. Full exam-format answers
    """
    system_prompt = f"You are a professor teaching {course_name}.\n\n" + teaching_philosophy + "\n\n" + course_prompt
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), MessagesPlaceholder("history"), ("human", "{question}")])
    model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    chain = prompt | model
    response = chain.invoke({"history": lc_history, "question": user_message})
    return response.content