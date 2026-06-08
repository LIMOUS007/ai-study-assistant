import streamlit as st
from core.retrieval import semantic_search
from core import database as db

_CATEGORIES = {
    "": "All Categories",
    "notes": "Notes",
    "slides": "Slides",
    "book": "Book",
    "assignment": "Assignment",
    "youtube": "YouTube",
}


def render_search(course: dict):
    course_id = course["id"]

    if not db.course_has_documents(course_id):
        st.info("No documents uploaded yet. Upload course material to use semantic search.")
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input(
            "Search",
            placeholder="e.g. deadlock, binary search, recursion...",
            label_visibility="collapsed",
            key=f"search_query_{course_id}",
        )
    with col2:
        category = st.selectbox(
            "Category",
            options=list(_CATEGORIES.keys()),
            format_func=lambda x: _CATEGORIES[x],
            label_visibility="collapsed",
            key=f"search_category_{course_id}",
        )

    if not query.strip():
        st.caption("Enter a query to search your course material by semantic similarity.")
        return

    with st.spinner("Searching..."):
        results = semantic_search(
            query=query.strip(),
            course_id=course_id,
            category=category if category else None,
            k=10,
        )

    if not results:
        st.info("No results found. Try a different query or remove the category filter.")
        return

    n = len(results)
    filter_label = f" in *{_CATEGORIES[category]}*" if category else ""
    st.caption(f"{n} result{'s' if n != 1 else ''} for **{query}**{filter_label}")

    for r in results:
        page_str = f", page {r['page']}" if r["page"] not in ("", 0) else ""
        cat_label = _CATEGORIES.get(r["category"], r["category"])
        score_pct = f"{max(0.0, r['score']):.0%}"

        with st.container(border=True):
            meta_col, score_col = st.columns([5, 1])
            with meta_col:
                st.markdown(f"**{r['source']}{page_str}**")
                st.caption(cat_label)
            with score_col:
                st.metric("Score", score_pct)
            st.markdown(r["excerpt"])
