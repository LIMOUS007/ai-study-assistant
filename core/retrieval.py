import httpx
import chromadb
from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser


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
    embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    vector_store = Chroma(client=client, embedding_function=embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})

    rag_instruction = (
        "\n\nAnswer using ONLY the course material provided below. "
        "Do not use prior knowledge outside the provided context.\n\n"
        "{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + rag_instruction),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ])
    model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))

    def run_chain(inputs: dict) -> str:
        docs = retriever.invoke(inputs["question"])
        context = _format_docs(docs)
        sources = _unique_sources(docs)

        answer = (
            prompt
            | model
            | StrOutputParser()
        ).invoke({
            "context": context,
            "history": inputs["history"],
            "question": inputs["question"],
        })

        if sources:
            source_lines = "\n".join(f"- {s}" for s in sources)
            answer += f"\n\n---\n**Sources**\n{source_lines}"

        return answer

    return RunnableLambda(run_chain)


def build_academic_rag_chain(course_id: str, system_prompt: str):
    # TODO: Academic mode RAG chain — same retriever as build_rag_chain, but uses
    # PydanticOutputParser(AcademicResponse) and returns a flattened markdown string.
    #
    # Steps:
    #   1. Set up vectorstore + retriever (copy the 4 lines from build_rag_chain)
    #   2. Import from core.teaching:
    #        from core.teaching import get_academic_parser, build_academic_prompt, academic_response_to_markdown
    #   3. Inside run_chain(inputs):
    #      a. Retrieve docs and format context (same as build_rag_chain)
    #      b. Build the prompt: prompt = build_academic_prompt(system_prompt)
    #      c. Get the parser: parser = get_academic_parser()
    #      d. Invoke the chain:
    #           result = (prompt | model | parser).invoke({
    #               "context": context,
    #               "history": inputs["history"],
    #               "question": inputs["question"],
    #           })
    #      e. Flatten: answer = academic_response_to_markdown(result)
    #      f. Append sources footnote (same pattern as build_rag_chain)
    #      g. Return answer
    #   4. Return RunnableLambda(run_chain)
    raise NotImplementedError("Implement build_academic_rag_chain() after core/teaching.py is ready")
