import shutil
import streamlit as st
from pathlib import Path
from core import database as db
from core.ingestion import ingest_file, delete_document_chunks


def render_upload_popover(course: dict):
    course_id = course["id"]

    if "upload_toast" in st.session_state:
        st.toast(st.session_state.pop("upload_toast"), icon="✅")

    # Dynamic key resets the uploader widget after each successful upload,
    # preventing Streamlit from re-triggering the upload on the next rerun.
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    with st.popover("📎"):
        st.markdown("**Upload Material**")

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
                vectorstore_path = Path("vectorstore") / course_id
                if vectorstore_path.exists():
                    shutil.rmtree(vectorstore_path)
                st.session_state.pop("confirm_clear_kb", None)
                st.session_state["upload_toast"] = "✓ Knowledge base cleared"
                st.rerun()
            if c2.button("Cancel", key="no_clear_kb", use_container_width=True):
                st.session_state.pop("confirm_clear_kb", None)
                st.rerun()
