import streamlit as st
from core import database as db
from core.chat import get_response
from ui.upload_view import render_upload_popover


def render_chat(course: dict):
    title_col, btn_col = st.columns([9, 1])
    with title_col:
        st.title(course["name"])
    with btn_col:
        st.write("")
        render_upload_popover(course)
    if course.get("course_prompt"):
        st.caption(f"📌 {course['course_prompt']}")

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
        # Save and display user message
        db.add_message(course["id"], "human", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        # Build history (everything before the message we just added)
        history = db.get_messages(course["id"])[:-1]

        # Get and display AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_response(
                    user_message=user_input,
                    course_name=course["name"],
                    course_prompt=course.get("course_prompt") or "",
                    chat_history=history,
                    course_id=course["id"], 
                )
            st.markdown(response)

        db.add_message(course["id"], "ai", response)
        st.rerun()
