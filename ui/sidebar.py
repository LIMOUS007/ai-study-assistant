import shutil
import streamlit as st
from pathlib import Path
from core import database as db
from core.ingestion import delete_vectorstore
from ui.upload_view import render_upload_popover


def render_sidebar():
    st.title("Study Assistant")
    st.caption("Your personal AI professor")
    st.divider()

    # --- Response mode ---
    if "chat_mode" not in st.session_state:
        st.session_state["chat_mode"] = "academic"
    st.radio(
        "Response mode",
        options=["academic", "quick"],
        format_func=lambda x: "Academic" if x == "academic" else "Quick Answer",
        key="chat_mode",
        help="Academic: structured 9-section format. Quick Answer: plain prose.",
    )
    st.divider()

    # --- New Course ---
    if st.button("+ New Course", use_container_width=True):
        st.session_state.creating_course = True
        st.session_state.editing_course_id = None

    if st.session_state.get("creating_course"):
        new_name = st.text_input("Course name", key="new_course_input", placeholder="e.g. Operating Systems")
        c1, c2 = st.columns(2)
        if c1.button("Create", key="confirm_create", use_container_width=True):
            if new_name.strip():
                course = db.create_course(new_name.strip())
                st.session_state.selected_course_id = course["id"]
                st.session_state.creating_course = False
                st.rerun()
        if c2.button("Cancel", key="cancel_create", use_container_width=True):
            st.session_state.creating_course = False
            st.rerun()

    st.divider()

    # --- Course List ---
    courses = db.get_all_courses()

    if not courses:
        st.caption("No courses yet.")
        return

    for course in courses:
        is_selected = st.session_state.get("selected_course_id") == course["id"]

        if st.button(
            f"{'▶ ' if is_selected else ''}{course['name']}",
            key=f"course_{course['id']}",
            use_container_width=True,
        ):
            st.session_state.selected_course_id = course["id"]
            st.session_state.editing_course_id = None
            st.session_state.confirm_delete_id = None
            st.rerun()

        # Controls only for the selected course
        if is_selected:
            c1, c2 = st.columns(2)
            if c1.button("✏ Edit", key=f"edit_{course['id']}", use_container_width=True):
                editing = st.session_state.get("editing_course_id") == course["id"]
                st.session_state.editing_course_id = None if editing else course["id"]
                st.rerun()
            if c2.button("🗑 Delete", key=f"del_{course['id']}", use_container_width=True):
                st.session_state.confirm_delete_id = course["id"]
                st.rerun()

            # Delete confirmation
            if st.session_state.get("confirm_delete_id") == course["id"]:
                st.warning(f"Delete **{course['name']}**? All chat history will be lost.")
                c1, c2 = st.columns(2)
                if c1.button("Yes", key=f"yes_del_{course['id']}", use_container_width=True):
                    delete_vectorstore(course["id"])
                    uploads = Path("data") / "courses" / course["id"]
                    if uploads.exists():
                        shutil.rmtree(uploads)
                    db.delete_course(course["id"])
                    st.session_state.selected_course_id = None
                    st.session_state.confirm_delete_id = None
                    st.rerun()
                if c2.button("No", key=f"no_del_{course['id']}", use_container_width=True):
                    st.session_state.confirm_delete_id = None
                    st.rerun()

            # Edit panel
            if st.session_state.get("editing_course_id") == course["id"]:
                st.divider()
                new_name = st.text_input(
                    "Course name", value=course["name"], key=f"rename_{course['id']}"
                )
                new_prompt = st.text_area(
                    "Course instructions",
                    value=course.get("course_prompt") or "",
                    placeholder="e.g. Answer in FLAME University exam style. Focus on proofs.",
                    key=f"prompt_{course['id']}",
                    height=120,
                )
                if st.button("Save", key=f"save_{course['id']}", use_container_width=True):
                    if new_name.strip():
                        db.update_course_name(course["id"], new_name.strip())
                    db.update_course_prompt(course["id"], new_prompt.strip())
                    st.session_state.editing_course_id = None
                    st.rerun()

            # Upload panel
            render_upload_popover(course)
            st.divider()
