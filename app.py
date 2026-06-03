import streamlit as st
from dotenv import load_dotenv
from core import database as db
from ui.sidebar import render_sidebar
from ui.chat_view import render_chat
from ui.upload_view import render_upload_view
load_dotenv()
db.init_db()

st.set_page_config(page_title="Study Assistant", layout="wide", page_icon="📚")

# Session state defaults
if "selected_course_id" not in st.session_state:
    st.session_state.selected_course_id = None

# Sidebar
with st.sidebar:
    render_sidebar()

# Main area
if st.session_state.selected_course_id:
    course = db.get_course(st.session_state.selected_course_id)
    if course:
        render_chat(course)
        render_upload_view(course)
    else:
        # Course was deleted externally
        st.session_state.selected_course_id = None
        st.rerun()
else:
    st.title("📚 Study Assistant")
    st.markdown("Select a course from the sidebar, or create a new one to get started.")
