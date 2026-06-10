import streamlit as st
from pathlib import Path
from core import database as db
from core.ingestion import ingest_file, ingest_youtube, delete_document_chunks, delete_vectorstore, update_document_metadata
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

_ERROR_KEY = "upload_error"
_TOAST_KEY = "upload_toast"


def _handle_youtube(course_id: str, url: str) -> bool:
    """Returns True on success, False on failure (error stored in session state)."""
    existing_urls = {d["source_url"] for d in db.get_documents(course_id) if d["source_url"]}
    if url in existing_urls:
        st.session_state[_ERROR_KEY] = "This video is already indexed."
        return False

    doc = db.add_document(course_id, "Loading...", "youtube", "youtube", source_url=url)
    try:
        with st.spinner("Fetching transcript and indexing..."):
            title, chunk_count = ingest_youtube(url, course_id, doc["id"])
        db.update_chunk_count(doc["id"], chunk_count)
        with db.get_connection() as conn:
            conn.execute("UPDATE documents SET filename = ? WHERE id = ?", (title, doc["id"]))
            conn.commit()
        st.session_state[_TOAST_KEY] = f"✓ {chunk_count} chunks indexed — {title}"
        return True
    except (TranscriptsDisabled, NoTranscriptFound):
        db.delete_document(doc["id"])
        st.session_state[_ERROR_KEY] = (
            "No transcript available for this video. "
            "Try a different lecture or check if captions are enabled."
        )
        return False
    except Exception as e:
        db.delete_document(doc["id"])
        st.session_state[_ERROR_KEY] = f"Failed to index video: {e}"
        return False


def render_upload_popover(course: dict):
    course_id = course["id"]

    if _TOAST_KEY in st.session_state:
        st.toast(st.session_state.pop(_TOAST_KEY), icon="✅")

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    with st.expander("📎 Upload Material"):

        # Persistent error banner — cleared when the user tries again
        if _ERROR_KEY in st.session_state:
            st.error(st.session_state.pop(_ERROR_KEY))

        tab_file, tab_text, tab_yt = st.tabs(["📄 File", "📝 Text", "▶️ YouTube"])

        with tab_file:
            uploaded_file = st.file_uploader(
                "File",
                type=["pdf", "pptx", "txt", "docx"],
                label_visibility="collapsed",
                key=f"uploader_{st.session_state.uploader_key}",
            )
            category = st.selectbox("Category", ["notes", "slides", "book", "assignment"])

            if uploaded_file:
                existing = {d["filename"] for d in db.get_documents(course_id)}
                if uploaded_file.name in existing:
                    st.warning(f"'{uploaded_file.name}' is already indexed. Delete it first to re-upload.")
                else:
                    save_dir = Path("data") / "courses" / course_id / "uploads"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / uploaded_file.name

                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    file_type = Path(uploaded_file.name).suffix.lower().lstrip(".")
                    doc = db.add_document(course_id, uploaded_file.name, file_type, category)

                    try:
                        with st.spinner("Indexing..."):
                            chunk_count = ingest_file(
                                str(save_path), course_id, uploaded_file.name, file_type, category, doc["id"]
                            )
                        db.update_chunk_count(doc["id"], chunk_count)
                        st.session_state.uploader_key += 1
                        st.session_state[_TOAST_KEY] = f"✓ {chunk_count} chunks indexed — {uploaded_file.name}"
                        st.rerun()
                    except Exception as e:
                        db.delete_document(doc["id"])
                        save_path.unlink(missing_ok=True)
                        st.session_state[_ERROR_KEY] = f"Failed to index file: {e}"
                        st.session_state.uploader_key += 1
                        st.rerun()

        with tab_text:
            text_title = st.text_input(
                "Title",
                placeholder="e.g. Week 3 Lecture Notes",
                key=f"text_title_{course_id}_{st.session_state.uploader_key}",
            )
            text_content = st.text_area(
                "Content",
                placeholder="Paste or type your notes here...",
                height=160,
                key=f"text_content_{course_id}_{st.session_state.uploader_key}",
            )
            text_category = st.selectbox(
                "Category",
                ["notes", "slides", "book", "assignment"],
                key=f"text_category_{course_id}",
            )
            can_add = bool(text_title.strip()) and bool(text_content.strip())
            if st.button("Add Notes", use_container_width=True, disabled=not can_add):
                filename = text_title.strip().replace("/", "-") + ".txt"
                existing = {d["filename"] for d in db.get_documents(course_id)}
                if filename in existing:
                    st.session_state[_ERROR_KEY] = f"'{filename}' is already indexed. Use a different title."
                    st.rerun()
                else:
                    save_dir = Path("data") / "courses" / course_id / "uploads"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / filename
                    save_path.write_text(text_content.strip(), encoding="utf-8")
                    doc = db.add_document(course_id, filename, "txt", text_category)
                    try:
                        with st.spinner("Indexing..."):
                            chunk_count = ingest_file(
                                str(save_path), course_id, filename, "txt", text_category, doc["id"]
                            )
                        db.update_chunk_count(doc["id"], chunk_count)
                        st.session_state.uploader_key += 1
                        st.session_state[_TOAST_KEY] = f"✓ {chunk_count} chunks indexed — {filename}"
                        st.rerun()
                    except Exception as e:
                        db.delete_document(doc["id"])
                        save_path.unlink(missing_ok=True)
                        st.session_state[_ERROR_KEY] = f"Failed to index text: {e}"
                        st.session_state.uploader_key += 1
                        st.rerun()

        with tab_yt:
            yt_url = st.text_input(
                "YouTube URL",
                placeholder="https://www.youtube.com/watch?v=...",
                key=f"yt_input_{course_id}",
            )
            if st.button("Add Lecture", use_container_width=True):
                if not yt_url.strip():
                    st.warning("Paste a YouTube URL first.")
                else:
                    success = _handle_youtube(course_id, yt_url.strip())
                    st.rerun()  # rerun either way — success shows toast, failure shows error banner

        # Document list
        docs = db.get_documents(course_id)
        if docs:
            st.divider()
            total_chunks = sum(d["chunk_count"] for d in docs)
            st.caption(f"{len(docs)} source{'s' if len(docs) > 1 else ''} · {total_chunks} chunks indexed")
            for doc in docs:
                edit_key = f"edit_doc_{doc['id']}"
                if st.session_state.get(edit_key):
                    new_name = st.text_input(
                        "Name", value=doc["filename"], key=f"name_{doc['id']}",
                    )
                    cat_options = ["notes", "slides", "book", "assignment", "youtube"]
                    cur_idx = cat_options.index(doc["document_category"]) if doc["document_category"] in cat_options else 0
                    new_category = st.selectbox(
                        "Category", cat_options, index=cur_idx, key=f"cat_{doc['id']}",
                    )
                    c1, c2 = st.columns(2)
                    if c1.button("Save", key=f"save_{doc['id']}", use_container_width=True):
                        new_name = new_name.strip()
                        if new_name:
                            db.update_document(doc["id"], filename=new_name, document_category=new_category)
                            update_document_metadata(course_id, doc["id"], source=new_name, category=new_category)
                        st.session_state.pop(edit_key, None)
                        st.rerun()
                    if c2.button("Cancel", key=f"cancel_{doc['id']}", use_container_width=True):
                        st.session_state.pop(edit_key, None)
                        st.rerun()
                else:
                    col1, col2, col3 = st.columns([5, 1, 1])
                    icon = "▶️" if doc["document_category"] == "youtube" else "📄"
                    label = f"{icon} {doc['filename']} · {doc['document_category']} · {doc['chunk_count']} chunks"
                    col1.caption(label)
                    if col2.button("✏️", key=f"editbtn_{doc['id']}"):
                        st.session_state[edit_key] = True
                        st.rerun()
                    if col3.button("✕", key=f"del_{doc['id']}"):
                        delete_document_chunks(course_id, doc["id"])
                        db.delete_document(doc["id"])
                        st.rerun()

            st.divider()
            if st.button("🗑️ Clear knowledge base", use_container_width=True):
                st.session_state["confirm_clear_kb"] = course_id

        if st.session_state.get("confirm_clear_kb") == course_id:
            st.warning("This deletes all documents and the vector store for this course.")
            c1, c2 = st.columns(2)
            if c1.button("Yes, clear", key="yes_clear_kb", use_container_width=True):
                for doc in db.get_documents(course_id):
                    db.delete_document(doc["id"])
                delete_vectorstore(course_id)
                st.session_state.pop("confirm_clear_kb", None)
                st.session_state[_TOAST_KEY] = "✓ Knowledge base cleared"
                st.rerun()
            if c2.button("Cancel", key="no_clear_kb", use_container_width=True):
                st.session_state.pop("confirm_clear_kb", None)
                st.rerun()
