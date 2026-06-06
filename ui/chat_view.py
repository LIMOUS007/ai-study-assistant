import streamlit as st
from core import database as db
from core.chat import get_response


def render_chat(course: dict):
    st.title(course["name"])
    if course.get("course_prompt"):
        st.caption(f"📌 {course['course_prompt']}")

    # Mode toggle — persists in session state for the duration of the session
    if "chat_mode" not in st.session_state:
        st.session_state["chat_mode"] = "academic"

    st.radio(
        "Response mode",
        options=["academic", "quick"],
        format_func=lambda x: "Academic" if x == "academic" else "Quick Answer",
        horizontal=True,
        key="chat_mode",
        label_visibility="collapsed",
        help="Academic: structured 9-section format (more tokens). Quick Answer: plain prose.",
    )

    # --- Message history ---
    messages = db.get_messages(course["id"])

    if not messages:
        st.info("No messages yet. Ask anything about this course.")

    for msg in messages:
        with st.chat_message("user" if msg["role"] == "human" else "assistant"):
            st.markdown(msg["content"])

    # --- Input ---
    user_input = st.chat_input(f"Ask anything about {course['name']}...")

    if user_input:
        db.add_message(course["id"], "human", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        history = db.get_messages(course["id"])[:-1]

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_response(
                    user_message=user_input,
                    course_name=course["name"],
                    course_prompt=course.get("course_prompt") or "",
                    chat_history=history,
                    course_id=course["id"],
                    mode=st.session_state["chat_mode"],
                )
            st.markdown(response)

        db.add_message(course["id"], "ai", response)
        st.rerun()
