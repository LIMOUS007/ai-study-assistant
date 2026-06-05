import shutil
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import httpx
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma


def ingest_file(file_path, course_id, filename, file_type, document_category, document_id) -> int:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    elif suffix == ".docx":
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata.update({
            "source": filename,
            "category": document_category,
            "course_id": course_id,
            "document_id": document_id,
        })

    embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    vectorstore_path = Path("vectorstore") / course_id
    vector_store = Chroma(embedding_function=embeddings, persist_directory=str(vectorstore_path))
    vector_store.add_documents(chunks)
    return len(chunks)


def delete_vectorstore(course_id: str):
    """Delete the entire per-course ChromaDB vector store.
    Explicitly releases all file handles first to avoid Windows file-lock errors.
    """
    import gc
    import chromadb
    vectorstore_path = Path("vectorstore") / course_id
    if not vectorstore_path.exists():
        return
    try:
        client = chromadb.PersistentClient(path=str(vectorstore_path))
        for col in client.list_collections():
            client.delete_collection(col.name)
        del client
        gc.collect()
    except Exception:
        pass
    shutil.rmtree(vectorstore_path, ignore_errors=True)


def delete_document_chunks(course_id: str, document_id: str):
    """Remove all Chroma chunks that belong to a specific document."""
    vectorstore_path = Path("vectorstore") / course_id
    if not vectorstore_path.exists():
        return
    embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    vector_store = Chroma(embedding_function=embeddings, persist_directory=str(vectorstore_path))
    result = vector_store._collection.get(where={"document_id": document_id})
    if result["ids"]:
        vector_store.delete(result["ids"])
