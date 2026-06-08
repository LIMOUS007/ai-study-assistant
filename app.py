import os
import ssl as _ssl
_orig_create_default_context = _ssl.create_default_context
def _no_verify_create_default_context(*args, **kwargs):
    ctx = _orig_create_default_context(*args, **kwargs)
    ctx.check_hostname = False
    ctx.verify_mode = _ssl.CERT_NONE
    return ctx
_ssl.create_default_context = _no_verify_create_default_context

import httpx as _httpx
_orig_httpx_client_init = _httpx.Client.__init__
def _no_verify_httpx_client_init(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    _orig_httpx_client_init(self, *args, **kwargs)
_httpx.Client.__init__ = _no_verify_httpx_client_init

_orig_httpx_async_client_init = _httpx.AsyncClient.__init__
def _no_verify_httpx_async_client_init(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    _orig_httpx_async_client_init(self, *args, **kwargs)
_httpx.AsyncClient.__init__ = _no_verify_httpx_async_client_init

import streamlit as st
from dotenv import load_dotenv
from core import database as db
from ui.sidebar import render_sidebar
from ui.chat_view import render_chat
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
    else:
        # Course was deleted externally
        st.session_state.selected_course_id = None
        st.rerun()
else:
    st.title("📚 Study Assistant")
    st.markdown("Select a course from the sidebar, or create a new one to get started.")
