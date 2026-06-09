from langchain_core.prompts import ChatPromptTemplate
from core.teaching import (
    _val, academic_response_to_markdown, build_academic_prompt,
    AcademicResponse, QAPair,
)


# ─── _val ─────────────────────────────────────────────────────────────────────

def test_val_returns_none_for_empty_string():
    assert _val("") is None


def test_val_returns_none_for_none():
    assert _val(None) is None


def test_val_returns_none_for_whitespace_only():
    assert _val("   ") is None


def test_val_returns_none_for_literal_null():
    assert _val("null") is None
    assert _val("NULL") is None


def test_val_returns_none_for_literal_none():
    assert _val("None") is None
    assert _val("NONE") is None


def test_val_returns_value_for_real_string():
    assert _val("hello") == "hello"


def test_val_returns_value_for_math_string():
    assert _val("$O(n)$") == "$O(n)$"


# ─── academic_response_to_markdown ────────────────────────────────────────────

def _make_response(**kwargs):
    defaults = dict(
        question_repeated="What is a stack?",
        professor_explanation="A stack is a LIFO structure.",
        beginner_explanation="Like a stack of plates.",
        analogy=None,
        theory_and_concepts="LIFO: Last In First Out.",
        worked_examples="push(1), push(2), pop() returns 2.",
        common_mistakes=None,
        practice_questions=[QAPair(question="Define stack.", answer="LIFO.")],
    )
    defaults.update(kwargs)
    return AcademicResponse(**defaults)


def test_markdown_includes_repeated_question():
    result = academic_response_to_markdown(_make_response())
    assert "What is a stack?" in result


def test_markdown_includes_professor_explanation():
    result = academic_response_to_markdown(_make_response())
    assert "LIFO structure" in result


def test_markdown_includes_theory():
    result = academic_response_to_markdown(_make_response())
    assert "Last In First Out" in result


def test_markdown_includes_worked_examples():
    result = academic_response_to_markdown(_make_response())
    assert "push(1)" in result


def test_markdown_includes_practice_questions():
    result = academic_response_to_markdown(_make_response())
    assert "Define stack." in result
    assert "LIFO." in result


def test_markdown_skips_none_analogy():
    result = academic_response_to_markdown(_make_response(analogy=None))
    assert result.count("None") == 0
    assert result.count("null") == 0


def test_markdown_includes_analogy_when_present():
    result = academic_response_to_markdown(_make_response(analogy="Like a stack of plates."))
    assert "stack of plates" in result


def test_markdown_skips_null_string_field():
    result = academic_response_to_markdown(_make_response(common_mistakes="null"))
    lines = result.lower().splitlines()
    assert not any(line.strip() == "null" for line in lines)


def test_markdown_multiple_practice_questions():
    resp = _make_response(
        practice_questions=[
            QAPair(question="Q1?", answer="A1."),
            QAPair(question="Q2?", answer="A2."),
        ]
    )
    result = academic_response_to_markdown(resp)
    assert "Q1?" in result
    assert "Q2?" in result
    assert "A1." in result
    assert "A2." in result


def test_markdown_empty_practice_questions():
    resp = _make_response(practice_questions=[])
    result = academic_response_to_markdown(resp)
    assert isinstance(result, str)


def test_markdown_separates_sections_with_newlines():
    result = academic_response_to_markdown(_make_response())
    assert "\n\n" in result


# ─── build_academic_prompt ────────────────────────────────────────────────────

def test_build_academic_prompt_returns_chat_prompt_template():
    prompt = build_academic_prompt("You are teaching CS.")
    assert isinstance(prompt, ChatPromptTemplate)


def test_build_academic_prompt_has_question_variable():
    prompt = build_academic_prompt("You are teaching CS.")
    assert "question" in prompt.input_variables


def test_build_academic_prompt_has_history_variable():
    prompt = build_academic_prompt("You are teaching CS.")
    assert "history" in prompt.input_variables


def test_build_academic_prompt_has_context_variable():
    prompt = build_academic_prompt("You are teaching CS.")
    assert "context" in prompt.input_variables


def test_build_academic_prompt_different_system_prompts():
    p1 = build_academic_prompt("Teach CS.")
    p2 = build_academic_prompt("Teach Math.")
    assert p1 is not p2
