from unittest.mock import MagicMock
from core.retrieval import _format_docs


def _make_doc(source="doc.pdf", page=None, content="Some content."):
    doc = MagicMock()
    doc.page_content = content
    doc.metadata = {"source": source}
    if page is not None:
        doc.metadata["page"] = page
    return doc


def test_format_docs_empty_list():
    assert _format_docs([]) == ""


def test_format_docs_includes_source():
    doc = _make_doc(source="lecture.pdf", content="CPU content")
    result = _format_docs([doc])
    assert "[Source: lecture.pdf]" in result
    assert "CPU content" in result


def test_format_docs_with_page_number():
    doc = _make_doc(source="notes.pdf", page=5, content="Page 5 text")
    result = _format_docs([doc])
    assert "[Source: notes.pdf, page 5]" in result


def test_format_docs_without_page_omits_page_str():
    doc = _make_doc(source="notes.txt", content="Some text")
    result = _format_docs([doc])
    assert ", page" not in result


def test_format_docs_page_zero_is_included():
    doc = _make_doc(source="book.pdf", page=0, content="Cover page")
    result = _format_docs([doc])
    assert ", page 0" in result  # page != "" check: integer 0 != "" is True, so page 0 is shown


def test_format_docs_multiple_docs_separated():
    doc1 = _make_doc(source="a.pdf", page=1, content="Content A")
    doc2 = _make_doc(source="b.pdf", page=2, content="Content B")
    result = _format_docs([doc1, doc2])
    assert "Content A" in result
    assert "Content B" in result
    assert "\n\n" in result


def test_format_docs_unknown_source_fallback():
    doc = MagicMock()
    doc.page_content = "Orphan content"
    doc.metadata = {}
    result = _format_docs([doc])
    assert "[Source: unknown]" in result
