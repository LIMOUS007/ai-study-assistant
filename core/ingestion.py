import shutil
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import httpx
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import YoutubeLoader

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

def _video_id_from_url(url: str) -> str:
    """Extract video ID from a YouTube URL for use as a fallback title."""
    import re
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else url


def ingest_youtube(url: str, course_id: str, document_id: str) -> tuple[str, int]:
    """
    Load YouTube transcript → split → embed → store in Chroma.
    Returns (video_title, chunk_count).

    Raises TranscriptsDisabled or NoTranscriptFound from youtube_transcript_api
    if captions are unavailable — let the caller handle those for the UI error message.
    """
    # add_video_info=False avoids the pytube dependency, which breaks with YouTube's current API.
    loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
    docs = loader.load()

    video_id = _video_id_from_url(url)
    title = f"YouTube: {video_id}"

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata.update({
            "source": title,
            "category": "youtube",
            "course_id": course_id,
            "document_id": document_id,
            "page": 0,
        })

    embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    vectorstore_path = Path("vectorstore") / course_id
    vector_store = Chroma(embedding_function=embeddings, persist_directory=str(vectorstore_path))
    vector_store.add_documents(chunks)
    return title, len(chunks)