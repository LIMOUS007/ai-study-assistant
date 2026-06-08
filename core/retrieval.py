import httpx
import chromadb
from pathlib import Path
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from core.teaching import get_academic_parser, build_academic_prompt, academic_response_to_markdown


RELEVANCE_THRESHOLD = 0.7


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
        label = f"{source}, page {page}" if page not in ("", 0) else source
        if label not in seen:
            seen.add(label)
            sources.append(label)
    return sources


def build_rag_chain(course_id: str, system_prompt: str):
    vectorstore_path = Path("vectorstore") / course_id
    # embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    vector_store = Chroma(client=client, embedding_function=embeddings)

    rag_instruction = (
        "\n\nAnswer using ONLY the course material provided below. "
        "Do not use prior knowledge outside the provided context.\n\n"
        "{context}"
    )
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + rag_instruction),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])
    plain_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])
    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    def run_chain(inputs: dict) -> str:
        docs = _filter_by_relevance(
            vector_store.similarity_search_with_relevance_scores(inputs["question"], k=4)
        )

        if not docs:
            return (plain_prompt | model | StrOutputParser()).invoke({
                "history": inputs["history"],
                "question": inputs["question"],
            })

        context = _format_docs(docs)
        sources = _unique_sources(docs)
        answer = (rag_prompt | model | StrOutputParser()).invoke({
            "context": context,
            "history": inputs["history"],
            "question": inputs["question"],
        })
        source_lines = "\n".join(f"- {s}" for s in sources)
        answer += f"\n\n---\n**Sources**\n{source_lines}"
        return answer

    return RunnableLambda(run_chain)


def build_academic_rag_chain(course_id: str, system_prompt: str):
    vectorstore_path = Path("vectorstore") / course_id
    # embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    vector_store = Chroma(client=client, embedding_function=embeddings)
    academic_prompt = build_academic_prompt(system_prompt)
    plain_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])
    parser = get_academic_parser()
    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    def run_chain(inputs: dict) -> str:
        docs = _filter_by_relevance(
            vector_store.similarity_search_with_relevance_scores(inputs["question"], k=4)
        )

        if not docs:
            return (plain_prompt | model | StrOutputParser()).invoke({
                "history": inputs["history"],
                "question": inputs["question"],
            })

        context = _format_docs(docs)
        sources = _unique_sources(docs)
        answer = academic_response_to_markdown(
            (academic_prompt | model | parser).invoke({
                "context": context,
                "history": inputs["history"],
                "question": inputs["question"],
            })
        )
        source_lines = "\n".join(f"- {s}" for s in sources)
        answer += f"\n\n---\n**Sources**\n{source_lines}"
        return answer

    return RunnableLambda(run_chain)
