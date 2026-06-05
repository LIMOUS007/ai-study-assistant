"""Tests for the course deletion cleanup logic (vectorstore + uploads)."""
import shutil
from pathlib import Path
import pytest
import core.database as db


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def _delete_course_with_cleanup(course_id: str, base: Path):
    """Mirrors the deletion logic in ui/sidebar.py."""
    for path in [
        base / "vectorstore" / course_id,
        base / "data" / "courses" / course_id,
    ]:
        if path.exists():
            shutil.rmtree(path)
    db.delete_course(course_id)


def test_vectorstore_folder_removed_on_delete(tmp_path):
    course = db.create_course("OS")
    vs_path = tmp_path / "vectorstore" / course["id"]
    vs_path.mkdir(parents=True)
    (vs_path / "chroma.sqlite3").write_text("fake chroma data")

    _delete_course_with_cleanup(course["id"], tmp_path)

    assert not vs_path.exists()


def test_uploads_folder_removed_on_delete(tmp_path):
    course = db.create_course("Math")
    uploads = tmp_path / "data" / "courses" / course["id"]
    uploads.mkdir(parents=True)
    (uploads / "notes.pdf").write_bytes(b"%PDF fake")

    _delete_course_with_cleanup(course["id"], tmp_path)

    assert not uploads.exists()


def test_delete_course_still_works_when_no_folders_exist(tmp_path):
    course = db.create_course("NoFiles")
    # Should not raise even if neither folder was ever created
    _delete_course_with_cleanup(course["id"], tmp_path)
    assert db.get_course(course["id"]) is None


def test_other_courses_vectorstore_untouched(tmp_path):
    c1 = db.create_course("Course 1")
    c2 = db.create_course("Course 2")

    for cid in [c1["id"], c2["id"]]:
        vs = tmp_path / "vectorstore" / cid
        vs.mkdir(parents=True)
        (vs / "chroma.sqlite3").write_text("data")

    _delete_course_with_cleanup(c1["id"], tmp_path)

    assert not (tmp_path / "vectorstore" / c1["id"]).exists()
    assert (tmp_path / "vectorstore" / c2["id"]).exists()
