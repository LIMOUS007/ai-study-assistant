import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "study_assistant.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                course_prompt TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id        TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


# --- Courses ---

def create_course(name: str) -> dict:
    course_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO courses (id, name) VALUES (?, ?)",
            (course_id, name)
        )
        conn.commit()
    return get_course(course_id)


def get_all_courses() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM courses ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_course(course_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
    return dict(row) if row else None


def update_course_name(course_id: str, name: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE courses SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name, course_id)
        )
        conn.commit()


def update_course_prompt(course_id: str, prompt: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE courses SET course_prompt = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (prompt, course_id)
        )
        conn.commit()


def delete_course(course_id: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()


# --- Chat Messages ---

def add_message(course_id: str, role: str, content: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, course_id, role, content) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), course_id, role, content)
        )
        conn.commit()


def get_messages(course_id: str) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE course_id = ? ORDER BY timestamp ASC",
            (course_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def delete_messages(course_id: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM chat_messages WHERE course_id = ?", (course_id,)
        )
        conn.commit()
