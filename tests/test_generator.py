from unittest.mock import patch, MagicMock
from core.generator import (
    _retrieve_multi_topic, _TOPIC_EXPANSIONS, generate_latex_notes,
    NoteDocument, NoteSection,
    QuizDocument, MCQQuestion,
    FlashcardDeck, Flashcard,
    PracticePaper, PaperSection, ExamQuestion,
    LatexNotesDocument, LatexSection, LatexSubsection,
    Flashcard, FlashcardDeck,
)


# ─── Pydantic models ──────────────────────────────────────────────────────────

def test_note_document_fields():
    doc = NoteDocument(
        title="Sorting", sections=[NoteSection(heading="Intro", content="Overview.")]
    )
    assert doc.title == "Sorting"
    assert doc.sections[0].heading == "Intro"
    assert doc.sections[0].content == "Overview."


def test_quiz_document_fields():
    q = MCQQuestion(
        question="What is O(n)?",
        options=["Constant", "Linear", "Quadratic", "Log"],
        correct="Linear",
        explanation="O(n) grows linearly.",
    )
    doc = QuizDocument(title="Quiz", questions=[q])
    assert doc.questions[0].correct == "Linear"
    assert len(doc.questions[0].options) == 4


def test_flashcard_deck_fields():
    deck = FlashcardDeck(
        title="DS Deck",
        cards=[Flashcard(front="What is LIFO?", back="Stack order — last in, first out.")],
    )
    assert deck.cards[0].front == "What is LIFO?"


def test_practice_paper_fields():
    paper = PracticePaper(
        course_name="CS101",
        sections=[
            PaperSection(
                section_name="A",
                instructions="Attempt all.",
                questions=[ExamQuestion(question="Define BFS.", marks=3, model_answer="...")],
            )
        ],
    )
    assert paper.course_name == "CS101"
    assert paper.sections[0].questions[0].marks == 3


def test_latex_notes_document_fields():
    doc = LatexNotesDocument(
        course_code="CS201",
        course_name="Algorithms",
        topic="Sorting",
        sections=[],
        complexity_table=[],
        final_checklist=[],
    )
    assert doc.course_code == "CS201"
    assert doc.sections == []


# ─── _TOPIC_EXPANSIONS ────────────────────────────────────────────────────────

def test_sorting_expands_to_five_algorithms():
    assert len(_TOPIC_EXPANSIONS["sorting"]) == 5


def test_sorting_aliases_match():
    assert _TOPIC_EXPANSIONS["sorting"] == _TOPIC_EXPANSIONS["sorting algorithms"]
    assert _TOPIC_EXPANSIONS["sorting"] == _TOPIC_EXPANSIONS["sorts"]


def test_linked_list_expands_to_two_entries():
    entries = _TOPIC_EXPANSIONS["linked list"]
    assert len(entries) == 2
    assert any("Singly" in e for e in entries)
    assert any("Doubly" in e for e in entries)


def test_stacks_and_queues_combined_has_both():
    combined = _TOPIC_EXPANSIONS["stacks and queues"]
    assert any("Stack" in t for t in combined)
    assert any("Queue" in t for t in combined)


def test_searching_expands_to_two():
    assert len(_TOPIC_EXPANSIONS["searching"]) == 2


# ─── _retrieve_multi_topic ────────────────────────────────────────────────────

@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_single_calls_once(mock_retrieve):
    mock_retrieve.return_value = "context"
    result = _retrieve_multi_topic("sorting", "course-1")
    mock_retrieve.assert_called_once_with("sorting", "course-1", k=12)
    assert result == "context"


@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_splits_comma(mock_retrieve):
    mock_retrieve.side_effect = lambda t, cid, k=6: f"ctx:{t}"
    result = _retrieve_multi_topic("sorting, searching", "course-1")
    assert "SORTING" in result
    assert "SEARCHING" in result


@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_splits_slash(mock_retrieve):
    mock_retrieve.side_effect = lambda t, cid, k=6: f"ctx:{t}"
    result = _retrieve_multi_topic("stacks/queues", "course-1")
    assert "STACKS" in result
    assert "QUEUES" in result


@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_splits_and(mock_retrieve):
    mock_retrieve.side_effect = lambda t, cid, k=6: f"ctx:{t}"
    result = _retrieve_multi_topic("arrays and trees", "course-1")
    assert "ARRAYS" in result
    assert "TREES" in result


@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_deduplicates_identical_context(mock_retrieve):
    mock_retrieve.return_value = "same context"
    result = _retrieve_multi_topic("sort, search", "course-1")
    assert result.count("same context") == 1


@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_fallback_when_all_empty(mock_retrieve):
    mock_retrieve.return_value = ""
    result = _retrieve_multi_topic("topic1, topic2", "course-1")
    assert result == ""


@patch("core.generator.retrieve_context")
def test_retrieve_multi_topic_skips_empty_subtopic_results(mock_retrieve):
    def side_effect(topic, cid, k=6):
        return "good context" if "sorting" in topic else ""
    mock_retrieve.side_effect = side_effect
    result = _retrieve_multi_topic("sorting, nothing", "course-1")
    assert "SORTING" in result
    assert "NOTHING" not in result


# ─── generate_latex_notes ─────────────────────────────────────────────────────

def _make_latex_doc(topic="Test"):
    return LatexNotesDocument(
        course_code="CS",
        course_name="Course",
        topic=topic,
        sections=[LatexSection(title=topic, subsections=[LatexSubsection(title="Sub")])],
        complexity_table=[],
        final_checklist=[f"{topic} fact"],
    )


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_unknown_topic_calls_single_once(mock_single):
    mock_single.return_value = _make_latex_doc("Thermodynamics")
    result = generate_latex_notes("Thermodynamics", "course-1")
    mock_single.assert_called_once()
    assert result.topic == "Thermodynamics"


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_sorting_expands_to_five_calls(mock_single):
    mock_single.return_value = _make_latex_doc()
    generate_latex_notes("Sorting", "course-1")
    assert mock_single.call_count == 5


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_merges_sections(mock_single):
    mock_single.side_effect = lambda t, cid, *a, **kw: LatexNotesDocument(
        course_code="CS", course_name="C", topic=t,
        sections=[LatexSection(title=t, subsections=[LatexSubsection(title="s")])],
        complexity_table=[], final_checklist=[f"fact-{t}"],
    )
    result = generate_latex_notes("Sorting", "course-1")
    assert len(result.sections) == 5


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_deduplicates_checklist(mock_single):
    mock_single.side_effect = lambda t, cid, *a, **kw: LatexNotesDocument(
        course_code="CS", course_name="C", topic=t,
        sections=[LatexSection(title=t, subsections=[LatexSubsection(title="s")])],
        complexity_table=[], final_checklist=["shared fact -> value"],
    )
    result = generate_latex_notes("Sorting", "course-1")
    assert result.final_checklist.count("shared fact -> value") == 1


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_calls_progress_callback(mock_single):
    mock_single.return_value = _make_latex_doc()
    calls = []
    generate_latex_notes(
        "Sorting", "course-1",
        progress_callback=lambda i, n, t: calls.append((i, n, t)),
    )
    assert len(calls) == 5
    assert calls[0][0] == 1
    assert calls[-1][0] == 5
    assert calls[-1][1] == 5


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_strips_syllabus_prefix(mock_single):
    mock_single.return_value = _make_latex_doc()
    generate_latex_notes("Syllabus: sorting", "course-1")
    assert mock_single.call_count == 5


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_comma_two_unknown_topics(mock_single):
    mock_single.side_effect = lambda t, cid, *a, **kw: _make_latex_doc(t)
    result = generate_latex_notes("Thermodynamics, Electrostatics", "course-1")
    assert mock_single.call_count == 2
    assert len(result.sections) == 2


@patch("core.generator._generate_latex_notes_single")
def test_generate_latex_notes_merged_topic_set_to_clean(mock_single):
    mock_single.side_effect = lambda t, cid, *a, **kw: _make_latex_doc(t)
    result = generate_latex_notes("Graphs, Trees", "course-1")
    assert result.topic == "Graphs, Trees"
