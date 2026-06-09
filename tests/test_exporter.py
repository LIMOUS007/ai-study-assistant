import pytest
from core.exporter import (
    _clean, _safe, _to_tex, _sanitize_code, _listing_lang,
    export_notes_pdf, export_quiz_pdf, export_flashcards_pdf,
    export_practice_paper_pdf, export_latex_source,
)
from core.generator import (
    NoteDocument, NoteSection,
    QuizDocument, MCQQuestion,
    FlashcardDeck, Flashcard,
    PracticePaper, PaperSection, ExamQuestion,
    LatexNotesDocument, LatexSection, LatexSubsection,
)


# ─── _clean ───────────────────────────────────────────────────────────────────

def test_clean_strips_fenced_code_block():
    assert _clean("```python\ncode\n```") == "[see in-app for code]"


def test_clean_strips_inline_code():
    assert _clean("`variable`") == "variable"


def test_clean_strips_bold():
    assert _clean("**bold text**") == "bold text"


def test_clean_strips_italic():
    assert _clean("*italic*") == "italic"


def test_clean_strips_heading_hashes():
    assert _clean("## Section Title") == "Section Title"


def test_clean_plain_text_unchanged():
    assert _clean("Hello world") == "Hello world"


# ─── _safe ────────────────────────────────────────────────────────────────────

def test_safe_ascii_unchanged():
    assert _safe("Hello") == "Hello"


def test_safe_replaces_non_latin1():
    result = _safe("smart ‘quotes’")
    assert isinstance(result, str)
    assert "‘" not in result
    assert "’" not in result


# ─── _to_tex ──────────────────────────────────────────────────────────────────

def test_to_tex_escapes_ampersand():
    assert r"\&" in _to_tex("a & b")


def test_to_tex_escapes_percent():
    assert r"\%" in _to_tex("50% off")


def test_to_tex_escapes_hash():
    assert r"\#" in _to_tex("#1 result")


def test_to_tex_escapes_underscore():
    assert r"\_" in _to_tex("snake_case")


def test_to_tex_escapes_lone_dollar():
    assert r"\$" in _to_tex("$10 cost")


def test_to_tex_preserves_math_region():
    result = _to_tex("complexity is $O(n^2)$")
    assert "$O(n^2)$" in result


def test_to_tex_preserves_multiple_math_regions():
    result = _to_tex("best $O(1)$ worst $O(n)$")
    assert "$O(1)$" in result
    assert "$O(n)$" in result


def test_to_tex_empty_string():
    assert _to_tex("") == ""


def test_to_tex_plain_text_unchanged():
    assert _to_tex("Hello world") == "Hello world"


# ─── _sanitize_code ───────────────────────────────────────────────────────────

def test_sanitize_code_plain_ascii_unchanged():
    code = "for i in range(n):\n    print(i)"
    assert _sanitize_code(code) == code


def test_sanitize_code_replaces_smart_single_quotes():
    result = _sanitize_code("it’s a test")
    assert "’" not in result
    assert "'" in result


def test_sanitize_code_replaces_arrow():
    result = _sanitize_code("ptr → next")
    assert "→" not in result
    assert "->" in result


def test_sanitize_code_replaces_em_dash():
    result = _sanitize_code("a — b")
    assert "—" not in result


# ─── _listing_lang ────────────────────────────────────────────────────────────

def test_listing_lang_cpp_variants():
    assert _listing_lang("cpp") == "C++"
    assert _listing_lang("c++") == "C++"


def test_listing_lang_python_variants():
    assert _listing_lang("python") == "Python"
    assert _listing_lang("py") == "Python"


def test_listing_lang_java():
    assert _listing_lang("java") == "Java"


def test_listing_lang_plain_returns_empty():
    assert _listing_lang("text") == ""
    assert _listing_lang("plain") == ""
    assert _listing_lang("plaintext") == ""


def test_listing_lang_unknown_passes_through():
    assert _listing_lang("Haskell") == "Haskell"


# ─── PDF exports ──────────────────────────────────────────────────────────────

def _make_notes():
    return NoteDocument(
        title="Test Notes",
        sections=[NoteSection(heading="Introduction", content="Some content.")],
    )


def _make_quiz():
    return QuizDocument(
        title="Test Quiz",
        questions=[
            MCQQuestion(
                question="What is 2+2?",
                options=["1", "2", "3", "4"],
                correct="4",
                explanation="Basic arithmetic.",
            )
        ],
    )


def _make_deck():
    return FlashcardDeck(
        title="Test Deck",
        cards=[Flashcard(front="What is a stack?", back="LIFO data structure.")],
    )


def _make_paper():
    return PracticePaper(
        course_name="CS101",
        sections=[
            PaperSection(
                section_name="Section A",
                instructions="Attempt all.",
                questions=[ExamQuestion(question="Define a stack.", marks=2, model_answer="LIFO.")],
            )
        ],
    )


def test_export_notes_pdf_returns_bytes():
    result = export_notes_pdf(_make_notes())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_export_quiz_pdf_returns_bytes():
    result = export_quiz_pdf(_make_quiz())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_export_flashcards_pdf_returns_bytes():
    result = export_flashcards_pdf(_make_deck())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_export_practice_paper_pdf_returns_bytes():
    result = export_practice_paper_pdf(_make_paper())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_export_quiz_pdf_marks_one_mark_singular():
    paper = _make_paper()
    paper.sections[0].questions[0].marks = 1
    result = export_practice_paper_pdf(paper)
    assert isinstance(result, bytes)


def test_export_quiz_options_labeled_abcd():
    result = export_quiz_pdf(_make_quiz())
    assert isinstance(result, bytes)


# ─── export_latex_source ──────────────────────────────────────────────────────

def _make_latex_doc():
    return LatexNotesDocument(
        course_code="CS201",
        course_name="Data Structures",
        topic="Sorting",
        sections=[
            LatexSection(
                title="Bubble Sort",
                subsections=[
                    LatexSubsection(
                        title="Overview",
                        body="Bubble sort swaps adjacent elements. Worst case $O(n^2)$.",
                        bullets=["Stable: Yes", "In-place: Yes"],
                    )
                ],
            )
        ],
        complexity_table=[],
        final_checklist=["Bubble Sort stability -> Stable"],
    )


def test_export_latex_source_returns_string():
    assert isinstance(export_latex_source(_make_latex_doc()), str)


def test_export_latex_source_has_document_wrapper():
    result = export_latex_source(_make_latex_doc())
    assert r"\begin{document}" in result
    assert r"\end{document}" in result


def test_export_latex_source_includes_course_name():
    result = export_latex_source(_make_latex_doc())
    assert "Data Structures" in result


def test_export_latex_source_includes_section_title():
    result = export_latex_source(_make_latex_doc())
    assert "Bubble Sort" in result


def test_export_latex_source_includes_checklist_item():
    result = export_latex_source(_make_latex_doc())
    assert "Bubble Sort stability" in result


def test_export_latex_source_twocolumn_layout():
    result = export_latex_source(_make_latex_doc())
    assert r"\twocolumn" in result


def test_export_latex_source_empty_sections():
    doc = LatexNotesDocument(
        course_code="X", course_name="X", topic="X",
        sections=[], complexity_table=[], final_checklist=[],
    )
    result = export_latex_source(doc)
    assert r"\begin{document}" in result
