import streamlit as st
from pathlib import Path
from core import database as db
from core.ingestion import ingest_file, ingest_youtube, delete_document_chunks, delete_vectorstore
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def _handle_youtube(course_id: str, url: str):
    existing_urls = {d["source_url"] for d in db.get_documents(course_id) if d["source_url"]}
    if url in existing_urls:
        st.warning("This video is already indexed.")
        return

    doc = db.add_document(course_id, "Loading...", "youtube", "youtube", source_url=url)
    try:
        with st.spinner("Fetching transcript and indexing..."):
            title, chunk_count = ingest_youtube(url, course_id, doc["id"])
        db.update_chunk_count(doc["id"], chunk_count)
        # patch filename to the real video title now that we have it
        with db.get_connection() as conn:
            conn.execute("UPDATE documents SET filename = ? WHERE id = ?", (title, doc["id"]))
            conn.commit()
        st.session_state["upload_toast"] = f"✓ {chunk_count} chunks indexed — {title}"
    except (TranscriptsDisabled, NoTranscriptFound):
        db.delete_document(doc["id"])
        st.error("No transcript available for this video. Try a different lecture or check if captions are enabled.")
    except Exception as e:
        db.delete_document(doc["id"])
        st.error(f"Failed to index video: {e}")


def render_upload_popover(course: dict):
    course_id = course["id"]

    if "upload_toast" in st.session_state:
        st.toast(st.session_state.pop("upload_toast"), icon="✅")

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    with st.expander("📎 Upload Material"):

        tab_file, tab_yt = st.tabs(["📄 File", "▶️ YouTube"])

        with tab_file:
            uploaded_file = st.file_uploader(
                "File",
                type=["pdf", "txt", "docx"],
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

                    with st.spinner("Indexing..."):
                        chunk_count = ingest_file(
                            str(save_path), course_id, uploaded_file.name, file_type, category, doc["id"]
                        )

                    db.update_chunk_count(doc["id"], chunk_count)
                    st.session_state.uploader_key += 1
                    st.session_state["upload_toast"] = f"✓ {chunk_count} chunks indexed — {uploaded_file.name}"
                    st.rerun()

        with tab_yt:
            yt_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
            if st.button("Add Lecture", use_container_width=True) and yt_url.strip():
                _handle_youtube(course_id, yt_url.strip())
                st.rerun()

        docs = db.get_documents(course_id)
        if docs:
            st.divider()
            total_chunks = sum(d["chunk_count"] for d in docs)
            st.caption(f"{len(docs)} file{'s' if len(docs) > 1 else ''} · {total_chunks} chunks indexed")
            for doc in docs:
                col1, col2 = st.columns([5, 1])
                col1.caption(f"{doc['filename']} · {doc['document_category']} · {doc['chunk_count']}")
                if col2.button("✕", key=f"del_{doc['id']}"):
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
                st.session_state["upload_toast"] = "✓ Knowledge base cleared"
                st.rerun()
            if c2.button("Cancel", key="no_clear_kb", use_container_width=True):
                st.session_state.pop("confirm_clear_kb", None)
                st.rerun()
