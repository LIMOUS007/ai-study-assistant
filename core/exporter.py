import re
from fpdf import FPDF
from core.generator import NoteDocument, QuizDocument, FlashcardDeck, PracticePaper


def _clean(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "[see in-app for code]", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"#{1,6}\s?", "", text)
    return text.strip()


def _safe(text: str) -> str:
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _new_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    return pdf


def export_notes_pdf(document: NoteDocument) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _safe(_clean(document.title)))
    pdf.ln(4)
    for section in document.sections:
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, _safe(_clean(section.heading)))
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _safe(_clean(section.content)))
        pdf.ln(5)
    return bytes(pdf.output())


def export_quiz_pdf(document: QuizDocument) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _safe(_clean(document.title)))
    pdf.ln(4)
    for i, q in enumerate(document.questions, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _safe(f"Q{i}. {_clean(q.question)}"))
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        for j, opt in enumerate(q.options):
            pdf.multi_cell(0, 6, _safe(f"  {chr(65 + j)}. {_clean(opt)}"))
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, _safe(f"Answer: {_clean(q.correct)}"))
        pdf.multi_cell(0, 6, _safe(f"Explanation: {_clean(q.explanation)}"))
        pdf.ln(5)
    return bytes(pdf.output())


def export_flashcards_pdf(deck: FlashcardDeck) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _safe(_clean(deck.title)))
    pdf.ln(4)
    for i, card in enumerate(deck.cards, 1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _safe(f"{i}. {_clean(card.front)}"))
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _safe(f"   {_clean(card.back)}"))
        pdf.ln(3)
    return bytes(pdf.output())


def export_practice_paper_pdf(paper: PracticePaper) -> bytes:
    pdf = _new_pdf()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, _safe(_clean(paper.course_name)))
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 12)
    pdf.multi_cell(0, 7, _safe("Practice Examination Paper"))
    pdf.ln(6)

    q_num = 1
    for section in paper.sections:
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 9, _safe(_clean(section.section_name)))
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 6, _safe(_clean(section.instructions)))
        pdf.ln(3)

        for q in section.questions:
            marks_label = f"[{q.marks} mark{'s' if q.marks != 1 else ''}]"
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, _safe(f"Q{q_num}. {_clean(q.question)}  {marks_label}"))
            pdf.ln(1)
            pdf.set_font("Helvetica", "I", 11)
            pdf.multi_cell(0, 6, _safe(f"Model Answer: {_clean(q.model_answer)}"))
            pdf.ln(4)
            q_num += 1

        pdf.ln(3)

    return bytes(pdf.output())
