from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from core import database as db
from core.llm import get_model, UsageTracker, PROVIDERS, with_provider_fallback
from core.retrieval import build_rag_chain, build_academic_rag_chain
from core.teaching import build_academic_prompt, academic_response_to_markdown, AcademicResponse, is_academic_question


def get_response(
    user_message: str,
    course_name: str,
    course_prompt: str,
    chat_history: list,
    course_id: str,
    mode: str = "academic",
    provider: str = "cerebras",
) -> tuple[str, dict]:
    """Returns (response_text, usage) where usage = {"model": label, "tokens": int}.

    If the selected provider hits a rate limit / quota error, automatically
    retries with the next configured provider (see core.llm.FALLBACK_ORDER).
    """
    (text, tracker), used_provider = with_provider_fallback(
        provider,
        lambda p: _generate(p, mode, user_message, course_name, course_prompt, chat_history, course_id),
    )
    usage = {
        "model": PROVIDERS[used_provider]["label"],
        "tokens": tracker.total_tokens or None,
    }
    return text, usage


def _generate(
    provider: str,
    mode: str,
    user_message: str,
    course_name: str,
    course_prompt: str,
    chat_history: list,
    course_id: str,
) -> tuple[str, UsageTracker]:
    lc_history = [
        HumanMessage(content=m["content"]) if m["role"] == "human" else AIMessage(content=m["content"])
        for m in chat_history
    ]
    model = get_model(provider)
    tracker = UsageTracker()
    invoke_cfg = {"callbacks": [tracker]}

    if mode == "quick":
        teaching_philosophy = (
            "You are a knowledgeable professor having a real conversation with a student — not filling out a form.\n\n"
            "When answering academic questions, your response should naturally flow through:\n"
            "- A precise technical explanation as a professor would give\n"
            "- A plain-language version or analogy that makes the concept click\n"
            "- The underlying theory, definitions, and key concepts\n"
            "- Worked examples that show the concept in action\n"
            "- Common mistakes or misconceptions students make\n"
            "- A few practice questions followed by full model answers\n\n"
            "Write in continuous, natural prose. Do NOT use rigid numbered sections, bold headers, or labels "
            "like \"Professor Explanation:\" or \"Beginner Explanation:\". The depth and structure should emerge "
            "from the content itself, like a great lecture. Be thorough but conversational."
        )
        system_prompt = f"You are a professor teaching {course_name}.\n\n{teaching_philosophy}\n\n{course_prompt}"
        if db.course_has_documents(course_id):
            chain = build_rag_chain(course_id, system_prompt, model)
            text = chain.invoke({"history": lc_history, "question": user_message}, config=invoke_cfg)
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder("history"),
                ("human", "{question}"),
            ])
            text = (prompt | model | StrOutputParser()).invoke(
                {"history": lc_history, "question": user_message}, config=invoke_cfg
            )

    else:  # academic
        system_prompt = f"You are a professor teaching {course_name}.\n\n{course_prompt}"
        if db.course_has_documents(course_id):
            chain = build_academic_rag_chain(course_id, system_prompt, model)
            text = chain.invoke({"history": lc_history, "question": user_message}, config=invoke_cfg)
        else:
            plain_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder("history"),
                ("human", "{question}"),
            ])
            if not is_academic_question(user_message, model):
                text = (plain_prompt | model | StrOutputParser()).invoke(
                    {"history": lc_history, "question": user_message}, config=invoke_cfg
                )
            else:
                academic_prompt = build_academic_prompt(system_prompt)
                result = (academic_prompt | model.with_structured_output(AcademicResponse)).invoke(
                    {"context": "", "history": lc_history, "question": user_message},
                    config=invoke_cfg,
                )
                text = academic_response_to_markdown(result)

    return text, tracker
