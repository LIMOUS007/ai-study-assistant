import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings


@st.cache_resource(show_spinner=False)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Load the sentence-transformer embedding model once per session."""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
