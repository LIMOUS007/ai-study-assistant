import pytest
from unittest.mock import patch, MagicMock
from core.ingestion import ingest_file, delete_document_chunks


def test_unsupported_file_type_raises(tmp_path):
    fake_file = tmp_path / "notes.pptx"
    fake_file.write_text("content")
    with pytest.raises(ValueError, match="Unsupported file type"):
        ingest_file(str(fake_file), "course-1", "notes.pptx", "pptx", "slides", "doc-1")


def test_delete_document_chunks_noop_when_vectorstore_missing():
    # Should silently do nothing when the vectorstore path doesn't exist
    delete_document_chunks("nonexistent-course-xyz", "nonexistent-doc-xyz")


@patch("core.ingestion.Chroma")
@patch("core.ingestion.OpenAIEmbeddings")
@patch("core.ingestion.RecursiveCharacterTextSplitter")
@patch("core.ingestion.TextLoader")
def test_ingest_txt_returns_chunk_count(mock_loader, mock_splitter, mock_embeddings, mock_chroma, tmp_path):
    fake_file = tmp_path / "notes.txt"
    fake_file.write_text("Some study notes.")

    fake_doc = MagicMock()
    fake_doc.metadata = {}
    mock_loader.return_value.load.return_value = [fake_doc]

    chunks = [MagicMock(metadata={}) for _ in range(3)]
    mock_splitter.return_value.split_documents.return_value = chunks

    mock_vs = MagicMock()
    mock_chroma.return_value = mock_vs

    count = ingest_file(str(fake_file), "course-1", "notes.txt", "txt", "notes", "doc-1")

    assert count == 3
    mock_vs.add_documents.assert_called_once()


@patch("core.ingestion.Chroma")
@patch("core.ingestion.OpenAIEmbeddings")
@patch("core.ingestion.RecursiveCharacterTextSplitter")
@patch("core.ingestion.PyPDFLoader")
def test_ingest_pdf_uses_pdf_loader(mock_loader, mock_splitter, mock_embeddings, mock_chroma, tmp_path):
    fake_file = tmp_path / "lecture.pdf"
    fake_file.write_bytes(b"%PDF fake")

    fake_doc = MagicMock()
    fake_doc.metadata = {}
    mock_loader.return_value.load.return_value = [fake_doc]
    mock_splitter.return_value.split_documents.return_value = [MagicMock(metadata={})]
    mock_chroma.return_value = MagicMock()

    ingest_file(str(fake_file), "c1", "lecture.pdf", "pdf", "slides", "d1")

    mock_loader.assert_called_once_with(str(fake_file))


@patch("core.ingestion.Chroma")
@patch("core.ingestion.OpenAIEmbeddings")
@patch("core.ingestion.RecursiveCharacterTextSplitter")
@patch("core.ingestion.TextLoader")
def test_chunk_metadata_is_set(mock_loader, mock_splitter, mock_embeddings, mock_chroma, tmp_path):
    fake_file = tmp_path / "notes.txt"
    fake_file.write_text("content")

    fake_doc = MagicMock()
    fake_doc.metadata = {}
    mock_loader.return_value.load.return_value = [fake_doc]

    chunk = MagicMock()
    chunk.metadata = {}
    mock_splitter.return_value.split_documents.return_value = [chunk]
    mock_chroma.return_value = MagicMock()

    ingest_file(str(fake_file), "cid", "notes.txt", "txt", "notes", "did")

    assert chunk.metadata["source"] == "notes.txt"
    assert chunk.metadata["category"] == "notes"
    assert chunk.metadata["course_id"] == "cid"
    assert chunk.metadata["document_id"] == "did"
