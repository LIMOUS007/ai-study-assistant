import chromadb
from pathlib import Path
from langchain_chroma import Chroma
from core.embeddings import get_embeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from core.teaching import build_academic_prompt, academic_response_to_markdown, AcademicResponse, is_academic_question


RELEVANCE_THRESHOLD = 0.3


def _filter_by_relevance(docs_and_scores: list) -> list:
    return [doc for doc, score in docs_and_scores if score >= RELEVANCE_THRESHOLD]


def _format_docs(docs) -> str:
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        page_str = f", page {page}" if page != "" else ""
        parts.append(f"[Source: {source}{page_str}]\n{doc.page_content}")
    return "\n\n".join(parts)


def _unique_sources(docs) -> list[str]:
    seen = set()
    sources = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        label = f"{source}, page {page}" if page != "" else source
        if label not in seen:
            seen.add(label)
            sources.append(label)
    return sources


def _get_vectorstore(course_id: str) -> Chroma:
    vectorstore_path = Path("vectorstore") / course_id
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    return Chroma(client=client, embedding_function=get_embeddings())


def build_rag_chain(course_id: str, system_prompt: str, model):
    vector_store = _get_vectorstore(course_id)
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nAnswer using ONLY the course material provided below. "
         "Do not use prior knowledge outside the provided context.\n\n{context}"),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])
    plain_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])

    def run_chain(inputs: dict) -> str:
        relevant_docs = _filter_by_relevance(
            vector_store.similarity_search_with_relevance_scores(inputs["question"], k=4)
        )

        if not relevant_docs:
            # No relevant course material — answer without RAG context or sources
            return (plain_prompt | model | StrOutputParser()).invoke({
                "history": inputs["history"],
                "question": inputs["question"],
            })

        context = _format_docs(relevant_docs)
        sources = _unique_sources(relevant_docs)
        answer = (rag_prompt | model | StrOutputParser()).invoke({
            "context": context,
            "history": inputs["history"],
            "question": inputs["question"],
        })
        source_lines = "\n".join(f"- {s}" for s in sources)
        return answer + f"\n\n---\n**Sources**\n{source_lines}"

    return RunnableLambda(run_chain)


def build_academic_rag_chain(course_id: str, system_prompt: str, model):
    vector_store = _get_vectorstore(course_id)
    academic_prompt = build_academic_prompt(system_prompt)
    plain_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])
    plain_rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nUse the course material below to answer.\n\n{context}"),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])

    def run_chain(inputs: dict) -> str:
        relevant_docs = _filter_by_relevance(
            vector_store.similarity_search_with_relevance_scores(inputs["question"], k=4)
        )

        if not relevant_docs:
            # No relevant course material — answer without RAG context or sources
            return (plain_prompt | model | StrOutputParser()).invoke({
                "history": inputs["history"],
                "question": inputs["question"],
            })

        context = _format_docs(relevant_docs)
        sources = _unique_sources(relevant_docs)
        source_lines = "\n".join(f"- {s}" for s in sources)

        if not is_academic_question(inputs["question"], model):
            answer = (plain_rag_prompt | model | StrOutputParser()).invoke({
                "context": context,
                "history": inputs["history"],
                "question": inputs["question"],
            })
        else:
            answer = academic_response_to_markdown(
                (academic_prompt | model.with_structured_output(AcademicResponse)).invoke({
                    "context": context,
                    "history": inputs["history"],
                    "question": inputs["question"],
                })
            )
        return answer + f"\n\n---\n**Sources**\n{source_lines}"

    return RunnableLambda(run_chain)


def semantic_search(query: str, course_id: str, category: str = None, k: int = 10) -> list[dict]:
    """Pure vector similarity search — no LLM. Returns ranked result dicts."""
    vectorstore_path = Path("vectorstore") / course_id
    if not vectorstore_path.exists():
        return []

    vector_store = _get_vectorstore(course_id)
    search_kwargs: dict = {"k": k}
    if category:
        search_kwargs["filter"] = {"category": {"$eq": category}}

    try:
        results = vector_store.similarity_search_with_relevance_scores(query, **search_kwargs)
    except Exception:
        results = []

    return [
        {
            "excerpt": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "category": doc.metadata.get("category", ""),
            "page": doc.metadata.get("page", ""),
            "score": round(score, 3),
        }
        for doc, score in results
    ]
