from pathlib import Path
from langchain_community.document_loaders import (PyPDFLoader, TextLoader, Docx2txtLoader)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import httpx
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
def ingest_file(file_path, course_id, filename, file_type, document_category, document_id) -> int:
    file_type = Path(file_path).suffix.lower()
    LOADERS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".docx": Docx2txtLoader,
    }
    if file_type not in LOADERS:
        raise ValueError(f"Unsupported file type: {file_type}")
    loader = LOADERS[file_type](file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size = 1000, chunk_overlap = 200)
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        chunk.metadata.update({
            "source": filename,
            "category": document_category,
            "course_id": course_id,
            "document_id": document_id
        })
    embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    vectorstore_path = Path("vectorstore") / course_id
    vector_store = Chroma(embedding_function=embeddings, persist_directory=str(vectorstore_path))   
    vector_store.add_documents(chunks)
    return len(chunks)
    
        