"""
App integration test. Run with: venv\Scripts\python run_app_tests.py
"""
import os, sys, tempfile, pathlib
from unittest.mock import patch

results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, name, detail))
    mark = "+" if status == "PASS" else "X"
    msg = f"  [{mark}] {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ─────────────────────────────────────────────
section("1. App loads (AppTest)")
# ─────────────────────────────────────────────
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=60)
at.run()

check("No crash on startup", not at.exception)
check("Title element rendered", len(at.title) > 0)
check("New Course button in sidebar",
      any("new course" in b.label.lower() or "+" in b.label for b in at.button))

# ─────────────────────────────────────────────
section("2. Sidebar buttons")
# ─────────────────────────────────────────────
button_labels = [b.label for b in at.button]
check("Buttons found", len(button_labels) > 0, str(button_labels))

# ─────────────────────────────────────────────
section("3. API key checker")
# ─────────────────────────────────────────────
from core.llm import check_api_key, is_configured

check("is_configured returns bool", isinstance(is_configured("cerebras"), bool))

no_key_result = check_api_key("cerebras") if not os.getenv("CEREBRAS_API_KEY") else {"status": "skipped"}
if no_key_result["status"] != "skipped":
    check("no_key status when unset", no_key_result["status"] == "no_key")

print("  Probing Cerebras API (live)...")
r = check_api_key("cerebras")
check("Cerebras key active", r["status"] == "active",
      f"status={r['status']} msg={r.get('message','')}")

print("  Probing OpenAI API (live)...")
r2 = check_api_key("openai")
check("OpenAI key reachable (active OR no_credits)",
      r2["status"] in ("active", "no_credits"),
      f"status={r2['status']} msg={r2.get('message','')}")

# ─────────────────────────────────────────────
section("4. Database CRUD")
# ─────────────────────────────────────────────
import core.database as db

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    with patch.object(db, "DB_PATH", pathlib.Path(tmp) / "t.db"):
        db.init_db()
        c = db.create_course("Integration Test")
        check("Create course", "id" in c)
        check("List courses", any(x["id"] == c["id"] for x in db.get_all_courses()))
        db.add_message(c["id"], "human", "test msg")
        check("Add and read message", len(db.get_messages(c["id"])) == 1)
        db.delete_course(c["id"])
        check("Delete cascades messages", db.get_messages(c["id"]) == [])
        check("Get deleted course returns None", db.get_course(c["id"]) is None)

# ─────────────────────────────────────────────
section("5. PDF export (all 4 types)")
# ─────────────────────────────────────────────
from core.exporter import export_notes_pdf, export_quiz_pdf, export_flashcards_pdf, export_practice_paper_pdf
from core.generator import (
    NoteDocument, NoteSection, QuizDocument, MCQQuestion,
    FlashcardDeck, Flashcard, PracticePaper, PaperSection, ExamQuestion,
)

pdf = export_notes_pdf(NoteDocument(
    title="Test", sections=[NoteSection(heading="H", content="Body $O(n)$")]
))
check("Notes PDF", pdf[:4] == b"%PDF", f"{len(pdf)} bytes")

pdf = export_quiz_pdf(QuizDocument(title="Q", questions=[
    MCQQuestion(question="Q?", options=["A","B","C","D"], correct="A", explanation="x")
]))
check("Quiz PDF", pdf[:4] == b"%PDF", f"{len(pdf)} bytes")

pdf = export_flashcards_pdf(FlashcardDeck(title="D", cards=[Flashcard(front="F", back="B")]))
check("Flashcard PDF", pdf[:4] == b"%PDF", f"{len(pdf)} bytes")

pdf = export_practice_paper_pdf(PracticePaper(course_name="CS", sections=[
    PaperSection(section_name="A", instructions="Attempt all.", questions=[
        ExamQuestion(question="Define stack.", marks=2, model_answer="LIFO.")
    ])
]))
check("Practice paper PDF", pdf[:4] == b"%PDF", f"{len(pdf)} bytes")

# ─────────────────────────────────────────────
section("6. Live chat - quick mode")
# ─────────────────────────────────────────────
print("  Calling LLM (quick mode)...")
from core.chat import get_response

with tempfile.TemporaryDirectory() as tmp:
    with patch.object(db, "DB_PATH", pathlib.Path(tmp) / "t.db"):
        db.init_db()
        c = db.create_course("Chat Test")
        try:
            text, usage = get_response(
                user_message="What is a stack data structure?",
                course_name="Data Structures",
                course_prompt="",
                chat_history=[],
                course_id=c["id"],
                mode="quick",
                provider="cerebras",
            )
            check("Quick mode returns text", len(text) > 30, f"{len(text)} chars")
            check("Usage has model label", bool(usage.get("model")))
        except Exception as e:
            check("Quick mode LLM call", False, str(e)[:100])

# ─────────────────────────────────────────────
section("7. Live chat - academic mode")
# ─────────────────────────────────────────────
print("  Calling LLM (academic mode)...")
with tempfile.TemporaryDirectory() as tmp:
    with patch.object(db, "DB_PATH", pathlib.Path(tmp) / "t.db"):
        db.init_db()
        c = db.create_course("Academic Test")
        try:
            text, usage = get_response(
                user_message="Explain bubble sort with an example",
                course_name="Data Structures",
                course_prompt="",
                chat_history=[],
                course_id=c["id"],
                mode="academic",
                provider="cerebras",
            )
            check("Academic mode returns text", len(text) > 30, f"{len(text)} chars")
            check("Academic mode - structured format sections present",
                  any(kw in text for kw in ["sort", "bubble", "swap", "pass"]))
        except Exception as e:
            check("Academic mode LLM call", False, str(e)[:100])

# ─────────────────────────────────────────────
section("8. Non-academic message in academic mode")
# ─────────────────────────────────────────────
print("  Testing non-academic detection...")
with tempfile.TemporaryDirectory() as tmp:
    with patch.object(db, "DB_PATH", pathlib.Path(tmp) / "t.db"):
        db.init_db()
        c = db.create_course("Convo Test")
        try:
            text, usage = get_response(
                user_message="Thanks for explaining that!",
                course_name="Data Structures",
                course_prompt="",
                chat_history=[],
                course_id=c["id"],
                mode="academic",
                provider="cerebras",
            )
            check("Non-academic msg gets plain reply", len(text) > 0, f"{len(text)} chars")
        except Exception as e:
            check("Non-academic detection", False, str(e)[:100])

# ─────────────────────────────────────────────
section("9. Multi-topic context retrieval (no vectorstore)")
# ─────────────────────────────────────────────
from unittest.mock import patch as mpatch
from core.generator import _retrieve_multi_topic

with mpatch("core.generator.retrieve_context", return_value="") as m:
    result = _retrieve_multi_topic("sorting, searching", "fake-id")
    check("Multi-topic falls back gracefully on empty context", result == "")

with mpatch("core.generator.retrieve_context", side_effect=lambda t, cid, k=6: f"ctx:{t}"):
    result = _retrieve_multi_topic("arrays, trees", "fake-id")
    check("Multi-topic splits and labels sections",
          "ARRAYS" in result and "TREES" in result)

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
print(f"\n{'='*55}")
passed = sum(1 for s,*_ in results if s == "PASS")
failed = sum(1 for s,*_ in results if s == "FAIL")
print(f"  RESULTS: {passed} passed, {failed} failed out of {len(results)}")
print(f"{'='*55}")
if failed:
    print("\nFailed:")
    for s, name, detail in results:
        if s == "FAIL":
            print(f"  X {name}" + (f": {detail}" if detail else ""))
sys.exit(0 if failed == 0 else 1)
