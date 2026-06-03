import streamlit as st
from pathlib import Path
from core import database as db
from core.ingestion import ingest_file


def render_upload_view(course: dict):
    course_id = course["id"]

    st.subheader("Knowledge Base")

    uploaded_file = st.file_uploader("Upload course material", type=["pdf", "txt", "docx"])
    category = st.selectbox("Category", ["notes", "slides", "book", "assignment"])

    if uploaded_file:
        save_dir = Path("data") / "courses" / course_id / "uploads"
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / uploaded_file.name

        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_type = Path(uploaded_file.name).suffix.lower().lstrip(".")
        doc = db.add_document(course_id, uploaded_file.name, file_type, category)

        with st.spinner(f"Ingesting {uploaded_file.name}..."):
            chunk_count = ingest_file(str(save_path), course_id, uploaded_file.name, file_type, category, doc["id"])

        db.update_chunk_count(doc["id"], chunk_count)
        st.success(f"Ingested {chunk_count} chunks from {uploaded_file.name}")
        st.rerun()

    docs = db.get_documents(course_id)
    if not docs:
        st.caption("No documents uploaded yet.")
        return

    by_category = {}
    for doc in docs:
        by_category.setdefault(doc["document_category"], []).append(doc)

    for cat, cat_docs in by_category.items():
        st.markdown(f"**{cat.capitalize()}**")
        for doc in cat_docs:
            col1, col2 = st.columns([5, 1])
            col1.markdown(f"- {doc['filename']} ({doc['chunk_count']} chunks)")
            if col2.button("Delete", key=doc["id"]):
                db.delete_document(doc["id"])
                st.rerun()
