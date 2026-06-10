import re
import streamlit as st
from core import database as db
from core.chat import get_response
from core.generator import generate_notes, generate_quiz, generate_flashcards, generate_practice_paper, generate_latex_notes
from core.exporter import export_notes_pdf, export_quiz_pdf, export_flashcards_pdf, export_practice_paper_pdf, export_latex_source, compile_latex_to_pdf
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
            if msg["role"] == "ai" and msg.get("model_label"):
                token_str = f"{msg['tokens']} tokens" if msg.get("tokens") else ""
                st.caption(msg["model_label"] + (f" · {token_str}" if token_str else ""))

    c1, c2, c3, _ = st.columns([1, 1, 1, 5])
    if c1.button("💬 Chat", type="primary", use_container_width=True):
        pass
    if c2.button("📚 Generate", use_container_width=True):
        st.session_state["view"] = "generate"
        st.rerun()
    if c3.button("🔍 Search", use_container_width=True):
        st.session_state["view"] = "search"
        st.rerun()

    if st.session_state.get("_auto_scroll"):
        del st.session_state["_auto_scroll"]
        st.iframe(
            """<script>
            setTimeout(function() {
                const main = window.parent.document.querySelector('section[data-testid="stMain"]');
                if (main) main.scrollTo({top: main.scrollHeight, behavior: 'smooth'});
            }, 150);
            </script>""",
            height=1,
        )

    user_input = st.chat_input(f"Ask anything about {course['name']}...")

    if user_input:
        db.add_message(course["id"], "human", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        history = db.get_messages(course["id"])[:-1]

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response, usage = get_response(
                        user_message=user_input,
                        course_name=course["name"],
                        course_prompt=course.get("course_prompt") or "",
                        chat_history=history,
                        course_id=course["id"],
                        mode=st.session_state["chat_mode"],
                        provider=st.session_state.get("provider", "cerebras"),
                    )
                except Exception as e:
                    err = str(e).lower()
                    if any(t in err for t in ("429", "rate limit", "rate_limit", "quota", "tpd", "tpm")):
                        st.error(
                            "⚠️ This provider's rate limit or daily quota was reached. "
                            "Switch the model provider in the sidebar, or wait and try again."
                        )
                    else:
                        st.error(f"⚠️ Something went wrong: {e}")
                    st.stop()
            st.markdown(response)
            token_str = f"{usage['tokens']} tokens" if usage.get("tokens") else ""
            st.caption(f"{usage['model']}" + (f" · {token_str}" if token_str else ""))

        st.session_state["_auto_scroll"] = True
        db.add_message(course["id"], "ai", response, model_label=usage["model"], tokens=usage.get("tokens"))
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

    gen_type = st.selectbox(
        "Type",
        ["Notes", "Quiz", "Flashcards", "Exam Prep", "Exam-Ready Notes (LaTeX)"],
    )

    if gen_type == "Exam Prep":
        exam_instructions = st.text_area(
            "Instructions (optional)",
            placeholder="e.g. Focus on chapters 3-5, include graph theory questions, weight long answers heavily",
            height=80,
        )
        can_generate = True
    else:
        # Topic history quick-select chips
        _hist_key = f"topic_hist_{course['id']}"
        _hist = st.session_state.get(_hist_key, [])
        if _hist:
            st.caption("Recent:")
            _hcols = st.columns(min(5, len(_hist)))
            for _i, _h in enumerate(_hist):
                if _hcols[_i].button(_h, key=f"hist_{_i}_{course['id']}", use_container_width=True):
                    st.session_state[f"topic_ti_{course['id']}"] = _h
                    st.rerun()

        topic = st.text_input(
            "Topic",
            placeholder="e.g. Deadlocks, Binary Search, Recursion",
            key=f"topic_ti_{course['id']}",
        )

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
        elif gen_type == "Flashcards":
            num_cards = st.slider("Number of cards", 5, 20, 10)
        elif gen_type == "Exam-Ready Notes (LaTeX)":
            st.caption("Generates two-column LaTeX notes with code blocks, exam callouts, and complexity tables — identical to Mohsin's format.")

        can_generate = bool(topic.strip())

    if st.button("⚡ Generate", type="primary", disabled=not can_generate):
        provider = st.session_state.get("provider", "cerebras")
        st.session_state.pop("latex_tex", None)
        st.session_state.pop("latex_pdf", None)
        st.session_state.pop("latex_pdf_log", None)
        try:
            if gen_type == "Notes":
                with st.spinner("Generating notes..."):
                    result = generate_notes(topic.strip(), note_type, course["id"], provider)
            elif gen_type == "Quiz":
                with st.spinner("Generating quiz..."):
                    result = generate_quiz(topic.strip(), course["id"], num_questions, provider)
            elif gen_type == "Flashcards":
                with st.spinner("Generating flashcards..."):
                    result = generate_flashcards(topic.strip(), course["id"], num_cards, provider)
            elif gen_type == "Exam-Ready Notes (LaTeX)":
                topic_str = topic.strip()
                _clean = re.sub(r'^[Ss]yllabus\s*:', '', topic_str, flags=re.IGNORECASE).strip()
                _major = [t.strip() for t in _clean.split(',') if t.strip()]
                if len(_major) > 1:
                    with st.status(f"Generating notes for {len(_major)} topics...", expanded=True) as _status:
                        def _cb(i, n, t):
                            _status.write(f"✓ Done: **{t}** ({i}/{n})")
                        result = generate_latex_notes(topic_str, course["id"], course["name"], provider, _cb)
                        _status.update(label=f"All {len(_major)} topics generated.", state="complete", expanded=False)
                else:
                    with st.spinner("Generating LaTeX exam notes..."):
                        result = generate_latex_notes(topic_str, course["id"], course["name"], provider)
                tex = export_latex_source(result)
                st.session_state["latex_tex"] = tex
                with st.spinner("Compiling PDF via remote API (up to ~60s)..."):
                    pdf_bytes, pdf_log = compile_latex_to_pdf(tex)
                st.session_state["latex_pdf"] = pdf_bytes
                st.session_state["latex_pdf_log"] = pdf_log
            else:
                with st.spinner("Generating exam paper..."):
                    result = generate_practice_paper(course["id"], course["name"], exam_instructions, provider)

            if gen_type != "Exam Prep":
                _hist_key = f"topic_hist_{course['id']}"
                _hist = st.session_state.get(_hist_key, [])
                _ts = topic.strip()
                if _ts and _ts not in _hist:
                    _hist.insert(0, _ts)
                    st.session_state[_hist_key] = _hist[:5]

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
        elif result_type == "Exam-Ready Notes (LaTeX)":
            _render_latex_notes(result)
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


def _render_latex_notes(doc):
    st.markdown(f"## {doc.course_name}: {doc.topic}")

    for sec in doc.sections:
        st.markdown(f"### {sec.title}")
        if sec.master_example:
            st.info(f"**Master Example:** `{sec.master_example}`")
        for sub in sec.subsections:
            st.markdown(f"**{sub.title}**")
            if sub.body:
                st.markdown(sub.body)
            if sub.mcq_facts:
                fact_md = " | ".join(f"**{f.label}:** {f.value}" for f in sub.mcq_facts)
                st.caption(fact_md)
            if sub.bullets:
                for b in sub.bullets:
                    st.markdown(f"- {b}")
            if sub.patterns:
                for pt in sub.patterns:
                    st.markdown(f"🔍 `{pt.keywords}` → **{pt.think}**")
            for we in sub.worked_examples:
                with st.expander(f"Example: {we.title}"):
                    if we.problem_statement:
                        st.markdown(f"*Problem:* {we.problem_statement}")
                    if we.answer_idea:
                        st.markdown(f"*Idea:* {we.answer_idea}")
                    if we.code:
                        st.code(we.code.code, language=we.code.language or "text")
                    if we.trace:
                        st.markdown(f"*Trace:* {we.trace}")
            for et in sub.exam_traces:
                with st.expander(f"Exam Q: {et.question[:60]}{'...' if len(et.question) > 60 else ''}"):
                    st.markdown(f"**Q:** {et.question}")
                    if et.steps:
                        for step in et.steps:
                            st.markdown(f"- {step}")
                    st.success(f"**Ans:** {et.answer}")
            if sub.exam_moves:
                st.info("**Exam move:** " + " · ".join(sub.exam_moves))
            if sub.pitfalls:
                st.warning("**Pitfall:** " + " · ".join(sub.pitfalls))
            if sub.ascii_diagrams:
                for diag in sub.ascii_diagrams:
                    st.code(diag, language="text")
            if sub.common_exam_questions:
                with st.expander("Common Exam Questions"):
                    for q in sub.common_exam_questions:
                        st.markdown(f"- {q}")
        if sec.comparison_table:
            ct = sec.comparison_table
            st.markdown(f"**{ct.title}**")
            st.table([
                {"Feature": r.feature, ct.left_label: r.left, ct.right_label: r.right}
                for r in ct.rows
            ])

    if doc.complexity_table:
        st.markdown("### Complexity Reference")
        st.table([
            {"Operation": r.operation, "Complexity": r.complexity, "Note": r.note}
            for r in doc.complexity_table
        ])

    if doc.final_checklist:
        st.markdown("### MCQ Quick Reference")
        mid = (len(doc.final_checklist) + 1) // 2
        col1, col2 = st.columns(2)
        with col1:
            for item in doc.final_checklist[:mid]:
                st.markdown(f"- {item}")
        with col2:
            for item in doc.final_checklist[mid:]:
                st.markdown(f"- {item}")

    st.divider()
    st.caption("Preview above shows structured content. The PDF/Overleaf version renders as two-column LaTeX with syntax-highlighted code and callout boxes.")

    pdf_bytes = st.session_state.get("latex_pdf")
    tex_src = st.session_state.get("latex_tex")
    pdf_log = st.session_state.get("latex_pdf_log", "")

    if pdf_bytes:
        import base64
        _b64 = base64.b64encode(pdf_bytes).decode()
        st.iframe(
            f'<iframe src="data:application/pdf;base64,{_b64}" '
            f'width="100%" height="700px" style="border:none;"></iframe>',
            height=720,
        )
        st.download_button(
            label="⬇ Download PDF",
            data=pdf_bytes,
            file_name=f"{doc.topic} - Exam Notes.pdf",
            mime="application/pdf",
        )
    elif pdf_log:
        with st.expander("PDF compilation log (all APIs failed)"):
            st.code(pdf_log, language="text")

    if tex_src:
        import html as _html
        escaped_tex = _html.escape(tex_src, quote=True)
        escaped_name = _html.escape(f"{doc.topic} - Exam Notes.tex", quote=True)
        st.iframe(
            f"""
            <form action="https://www.overleaf.com/docs" method="post" target="_blank" style="display:inline-block;margin-right:8px">
              <input type="hidden" name="snip" value="{escaped_tex}">
              <input type="hidden" name="snip_name" value="{escaped_name}">
              <button type="submit" style="background:#4CAF50;color:white;padding:8px 18px;border:none;border-radius:4px;cursor:pointer;font-size:14px;font-weight:600;">
                📄 Open in Overleaf (compile → PDF)
              </button>
            </form>
            """,
            height=50,
        )
        st.download_button(
            label="⬇ Download .tex source",
            data=tex_src.encode("utf-8"),
            file_name=f"{doc.topic} - Exam Notes.tex",
            mime="text/plain",
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
