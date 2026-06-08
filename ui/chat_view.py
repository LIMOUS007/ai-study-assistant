import streamlit as st
from core import database as db
from core.chat import get_response
from core.generator import generate_notes, generate_quiz, generate_flashcards, generate_practice_paper
from core.exporter import export_notes_pdf, export_quiz_pdf, export_flashcards_pdf, export_practice_paper_pdf
from ui.search_view import render_search


def render_chat(course: dict):
    st.title(course["name"])
    if course.get("course_prompt"):
        st.caption(f"📌 {course['course_prompt']}")

    if "view" not in st.session_state:
        st.session_state["view"] = "chat"

    if st.session_state["view"] == "chat":
        _render_chat_tab(course)
    elif st.session_state["view"] == "generate":
        _render_generate_tab(course)
    else:
        _render_search_tab(course)


def _render_chat_tab(course: dict):
    messages = db.get_messages(course["id"])

    if not messages:
        st.info("No messages yet. Ask anything about this course.")

    for msg in messages:
        with st.chat_message("user" if msg["role"] == "human" else "assistant"):
            st.markdown(msg["content"])

    c1, c2, c3, _ = st.columns([1, 1, 1, 5])
    if c1.button("💬 Chat", type="primary", use_container_width=True):
        pass
    if c2.button("📚 Generate", use_container_width=True):
        st.session_state["view"] = "generate"
        st.rerun()
    if c3.button("🔍 Search", use_container_width=True):
        st.session_state["view"] = "search"
        st.rerun()

    user_input = st.chat_input(f"Ask anything about {course['name']}...")

    if user_input:
        db.add_message(course["id"], "human", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        history = db.get_messages(course["id"])[:-1]

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response, usage = get_response(
                    user_message=user_input,
                    course_name=course["name"],
                    course_prompt=course.get("course_prompt") or "",
                    chat_history=history,
                    course_id=course["id"],
                    mode=st.session_state["chat_mode"],
                    provider=st.session_state.get("provider", "cerebras"),
                )
            st.markdown(response)
            token_str = f"{usage['tokens']} tokens" if usage.get("tokens") else ""
            st.caption(f"{usage['model']}" + (f" · {token_str}" if token_str else ""))

        db.add_message(course["id"], "ai", response)
        st.rerun()


def _render_generate_tab(course: dict):
    c1, c2, c3, _ = st.columns([1, 1, 1, 5])
    if c1.button("💬 Chat", use_container_width=True):
        st.session_state["view"] = "chat"
        st.rerun()
    if c2.button("📚 Generate", type="primary", use_container_width=True):
        pass
    if c3.button("🔍 Search", use_container_width=True):
        st.session_state["view"] = "search"
        st.rerun()

    st.subheader("Generate Study Materials")

    gen_type = st.selectbox("Type", ["Notes", "Quiz", "Flashcards", "Exam Prep"])

    if gen_type == "Exam Prep":
        exam_instructions = st.text_area(
            "Instructions (optional)",
            placeholder="e.g. Focus on chapters 3-5, include graph theory questions, weight long answers heavily",
            height=80,
        )
        can_generate = True
    else:
        topic = st.text_input("Topic", placeholder="e.g. Deadlocks, Binary Search, Recursion")

        if gen_type == "Notes":
            note_type = st.selectbox(
                "Note style",
                ["detailed", "revision", "exam", "cheat_sheet"],
                format_func=lambda x: {
                    "detailed": "Detailed Notes",
                    "revision": "Revision Notes",
                    "exam": "Exam Notes",
                    "cheat_sheet": "Cheat Sheet",
                }[x],
            )
        elif gen_type == "Quiz":
            num_questions = st.slider("Number of questions", 3, 15, 5)
        else:
            num_cards = st.slider("Number of cards", 5, 20, 10)

        can_generate = bool(topic.strip()) if gen_type != "Exam Prep" else True

    if st.button("⚡ Generate", type="primary", disabled=not can_generate):
        with st.spinner(f"Generating {gen_type.lower()}..."):
            provider = st.session_state.get("provider", "cerebras")
            try:
                if gen_type == "Notes":
                    result = generate_notes(topic.strip(), note_type, course["id"], provider)
                elif gen_type == "Quiz":
                    result = generate_quiz(topic.strip(), course["id"], num_questions, provider)
                elif gen_type == "Flashcards":
                    result = generate_flashcards(topic.strip(), course["id"], num_cards, provider)
                else:
                    result = generate_practice_paper(course["id"], course["name"], exam_instructions, provider)
                st.session_state["gen_result"] = result
                st.session_state["gen_type"] = gen_type
                st.session_state["gen_course_id"] = course["id"]
                st.session_state["fc_idx"] = 0
                st.session_state["fc_flipped"] = False
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Generation failed: {e}")

    if (
        "gen_result" in st.session_state
        and "gen_type" in st.session_state
        and st.session_state.get("gen_course_id") == course["id"]
    ):
        st.divider()
        result = st.session_state["gen_result"]
        result_type = st.session_state["gen_type"]
        if result_type == "Notes":
            _render_notes(result)
        elif result_type == "Quiz":
            _render_quiz(result)
        elif result_type == "Flashcards":
            _render_flashcards(result)
        else:
            _render_practice_paper(result)


def _render_notes(document):
    st.markdown(f"## {document.title}")
    for section in document.sections:
        st.markdown(f"### {section.heading}")
        st.markdown(section.content)
    pdf_bytes = export_notes_pdf(document)
    st.download_button(
        label="⬇ Download PDF",
        data=pdf_bytes,
        file_name=f"{document.title}.pdf",
        mime="application/pdf",
    )


def _render_quiz(document):
    st.markdown(f"## {document.title}")
    for i, q in enumerate(document.questions, 1):
        st.markdown(f"**Q{i}. {q.question}**")
        for j, opt in enumerate(q.options):
            st.markdown(f"- {chr(65 + j)}. {opt}")
        with st.expander("Show Answer"):
            st.success(f"**Correct:** {q.correct}")
            st.markdown(q.explanation)
        st.divider()
    pdf_bytes = export_quiz_pdf(document)
    st.download_button(
        label="⬇ Download PDF",
        data=pdf_bytes,
        file_name=f"{document.title}.pdf",
        mime="application/pdf",
    )


def _render_flashcards(deck):
    cards = deck.cards
    idx = st.session_state.get("fc_idx", 0)
    flipped = st.session_state.get("fc_flipped", False)

    st.markdown(f"## {deck.title}")
    st.caption(f"Card {idx + 1} of {len(cards)}")

    card = cards[idx]
    if flipped:
        st.info(f"**Back**\n\n{card.back}")
    else:
        st.info(f"**Front**\n\n{card.front}")

    c1, c2, c3 = st.columns(3)
    if c1.button("← Prev", disabled=idx == 0, use_container_width=True):
        st.session_state["fc_idx"] = idx - 1
        st.session_state["fc_flipped"] = False
        st.rerun()
    if c2.button("Flip ↔", use_container_width=True):
        st.session_state["fc_flipped"] = not flipped
        st.rerun()
    if c3.button("Next →", disabled=idx == len(cards) - 1, use_container_width=True):
        st.session_state["fc_idx"] = idx + 1
        st.session_state["fc_flipped"] = False
        st.rerun()

    st.divider()
    pdf_bytes = export_flashcards_pdf(deck)
    st.download_button(
        label="⬇ Download as PDF",
        data=pdf_bytes,
        file_name=f"{deck.title}.pdf",
        mime="application/pdf",
    )


def _render_practice_paper(paper):
    st.markdown(f"## {paper.course_name}")
    st.caption("Practice Examination Paper")

    q_num = 1
    for section in paper.sections:
        st.markdown(f"### {section.section_name}")
        st.caption(section.instructions)
        for q in section.questions:
            marks_label = f"[{q.marks} mark{'s' if q.marks != 1 else ''}]"
            st.markdown(f"**Q{q_num}. {q.question}** `{marks_label}`")
            with st.expander("Model Answer"):
                st.markdown(q.model_answer)
            q_num += 1
        st.divider()

    pdf_bytes = export_practice_paper_pdf(paper)
    st.download_button(
        label="⬇ Download PDF",
        data=pdf_bytes,
        file_name=f"{paper.course_name} - Practice Paper.pdf",
        mime="application/pdf",
    )


def _render_search_tab(course: dict):
    c1, c2, c3, _ = st.columns([1, 1, 1, 5])
    if c1.button("💬 Chat", use_container_width=True):
        st.session_state["view"] = "chat"
        st.rerun()
    if c2.button("📚 Generate", use_container_width=True):
        st.session_state["view"] = "generate"
        st.rerun()
    if c3.button("🔍 Search", type="primary", use_container_width=True):
        pass

    st.subheader("Semantic Search")
    render_search(course)
