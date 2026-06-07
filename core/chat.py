import httpx
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from core import database as db
from core.retrieval import build_rag_chain, build_academic_rag_chain
from core.teaching import get_academic_parser, build_academic_prompt, academic_response_to_markdown


def get_response(
    user_message: str,
    course_name: str,
    course_prompt: str,
    chat_history: list,
    course_id: str,
    mode: str = "academic",
) -> str:
    lc_history = []
    for message in chat_history:
        if message["role"] == "human":
            lc_history.append(HumanMessage(content=message["content"]))
        elif message["role"] == "ai":
            lc_history.append(AIMessage(content=message["content"]))

    model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))

    if mode == "quick":
        teaching_philosophy = """
You are a knowledgeable professor having a real conversation with a student — not filling out a form.

When answering academic questions, your response should naturally flow through:
- A precise technical explanation as a professor would give
- A plain-language version or analogy that makes the concept click
- The underlying theory, definitions, and key concepts
- Worked examples that show the concept in action
- Common mistakes or misconceptions students make
- A few practice questions followed by full model answers

Write in continuous, natural prose. Do NOT use rigid numbered sections, bold headers, or labels like "Professor Explanation:" or "Beginner Explanation:". The depth and structure should emerge from the content itself, like a great lecture. Be thorough but conversational.
        """
        system_prompt = f"You are a professor teaching {course_name}.\n\n{teaching_philosophy}\n\n{course_prompt}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ])
        if db.course_has_documents(course_id):
            chain = build_rag_chain(course_id, system_prompt)
            return chain.invoke({"history": lc_history, "question": user_message})
        else:
            chain = prompt | model
            return chain.invoke({"history": lc_history, "question": user_message}).content

    else:  # academic
        system_prompt = f"You are a professor teaching {course_name}.\n\n{course_prompt}"
        if db.course_has_documents(course_id):
            chain = build_academic_rag_chain(course_id, system_prompt)
            return chain.invoke({"history": lc_history, "question": user_message})
        else:
            parser = get_academic_parser()
            prompt = build_academic_prompt(system_prompt)
            result = (prompt | model | parser).invoke({
                "context": "",
                "history": lc_history,
                "question": user_message,
            })
            return academic_response_to_markdown(result)
