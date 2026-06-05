import pytest
import core.database as db


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


# --- Courses ---

def test_create_course_returns_dict():
    course = db.create_course("Physics")
    assert course["name"] == "Physics"
    assert "id" in course
    assert course["course_prompt"] is None


def test_get_all_courses_empty():
    assert db.get_all_courses() == []


def test_get_all_courses_returns_all():
    db.create_course("Math")
    db.create_course("Chemistry")
    assert len(db.get_all_courses()) == 2


def test_get_course_returns_none_for_missing():
    assert db.get_course("nonexistent-id") is None


def test_get_course_returns_course():
    course = db.create_course("History")
    fetched = db.get_course(course["id"])
    assert fetched["name"] == "History"


def test_update_course_name():
    course = db.create_course("Old Name")
    db.update_course_name(course["id"], "New Name")
    assert db.get_course(course["id"])["name"] == "New Name"


def test_update_course_prompt():
    course = db.create_course("Math")
    db.update_course_prompt(course["id"], "Answer with proofs.")
    assert db.get_course(course["id"])["course_prompt"] == "Answer with proofs."


def test_delete_course_removes_it():
    course = db.create_course("ToDelete")
    db.delete_course(course["id"])
    assert db.get_course(course["id"]) is None


def test_delete_course_cascades_messages():
    course = db.create_course("WithMessages")
    db.add_message(course["id"], "human", "hello")
    db.delete_course(course["id"])
    assert db.get_messages(course["id"]) == []


def test_delete_course_cascades_documents():
    course = db.create_course("WithDocs")
    db.add_document(course["id"], "notes.pdf", "pdf", "notes")
    db.delete_course(course["id"])
    assert db.get_documents(course["id"]) == []


# --- Documents ---

def test_add_document_returns_dict():
    course = db.create_course("Biology")
    doc = db.add_document(course["id"], "lecture1.pdf", "pdf", "slides")
    assert doc["filename"] == "lecture1.pdf"
    assert doc["file_type"] == "pdf"
    assert doc["document_category"] == "slides"
    assert doc["chunk_count"] == 0


def test_get_document_returns_none_for_missing():
    assert db.get_document("nonexistent") is None


def test_get_documents_empty():
    course = db.create_course("Empty")
    assert db.get_documents(course["id"]) == []


def test_get_documents_isolates_by_course():
    c1 = db.create_course("Course 1")
    c2 = db.create_course("Course 2")
    db.add_document(c1["id"], "file1.pdf", "pdf", "notes")
    db.add_document(c2["id"], "file2.pdf", "pdf", "notes")
    docs = db.get_documents(c1["id"])
    assert len(docs) == 1
    assert docs[0]["filename"] == "file1.pdf"


def test_update_chunk_count():
    course = db.create_course("CS")
    doc = db.add_document(course["id"], "book.txt", "txt", "book")
    db.update_chunk_count(doc["id"], 42)
    assert db.get_document(doc["id"])["chunk_count"] == 42


def test_delete_document():
    course = db.create_course("DeleteDoc")
    doc = db.add_document(course["id"], "remove.pdf", "pdf", "notes")
    db.delete_document(doc["id"])
    assert db.get_document(doc["id"]) is None


def test_course_has_documents_false_when_empty():
    course = db.create_course("NoDocs")
    assert db.course_has_documents(course["id"]) is False


def test_course_has_documents_true_when_has_docs():
    course = db.create_course("HasDocs")
    db.add_document(course["id"], "notes.pdf", "pdf", "notes")
    assert db.course_has_documents(course["id"]) is True


def test_course_has_documents_false_after_delete():
    course = db.create_course("DeleteThenCheck")
    doc = db.add_document(course["id"], "notes.pdf", "pdf", "notes")
    db.delete_document(doc["id"])
    assert db.course_has_documents(course["id"]) is False


# --- Chat Messages ---

def test_add_and_get_messages_ordered():
    course = db.create_course("Chat")
    db.add_message(course["id"], "human", "What is a CPU?")
    db.add_message(course["id"], "ai", "A CPU is the brain of a computer.")
    messages = db.get_messages(course["id"])
    assert len(messages) == 2
    assert messages[0]["role"] == "human"
    assert messages[1]["role"] == "ai"
    assert messages[0]["content"] == "What is a CPU?"


def test_get_messages_empty():
    course = db.create_course("EmptyChat")
    assert db.get_messages(course["id"]) == []


def test_delete_messages_clears_history():
    course = db.create_course("ClearChat")
    db.add_message(course["id"], "human", "hello")
    db.delete_messages(course["id"])
    assert db.get_messages(course["id"]) == []


def test_messages_isolated_between_courses():
    c1 = db.create_course("Course A")
    c2 = db.create_course("Course B")
    db.add_message(c1["id"], "human", "msg for A")
    assert db.get_messages(c2["id"]) == []
