# Milestone 2 — Knowledge Base + RAG

## Goal

Replace the plain LLM chain with a Retrieval-Augmented Generation (RAG) pipeline. The assistant will answer questions grounded in uploaded course material (PDFs, PPTX, TXT) and cite sources by filename and page number.

---

## How RAG Works (Concept First)

RAG has two separate pipelines:

### Ingestion (runs once per uploaded file)
```
File → DocumentLoader → chunks → OpenAIEmbeddings → ChromaDB
```
Each chunk is stored alongside its vector embedding and metadata (filename, page, category, course_id).

### Retrieval (runs on every user message)
```
User question → embed → similarity search in Chroma → top-k chunks → inject into prompt → LLM → answer
```
The LLM only sees the retrieved chunks as context — it cannot hallucinate beyond what was uploaded.

---

## Packages to Install

```
pip install chromadb pypdf python-pptx langchain-community
```

Update `requirements.txt` to add:
```
chromadb
pypdf
python-pptx
```
(`langchain-community` is already listed.)

---

## New Files

| File | Written by | Purpose |
|---|---|---|
| `core/ingestion.py` | You | Load → split → embed → store in Chroma |
| `core/retrieval.py` | You | Build retriever + RAG chain per course |
| `ui/upload_view.py` | Generated | File uploader widget + document list |

## Modified Files

| File | Written by | Change |
|---|---|---|
| `core/database.py` | Generated | Add `documents` table + CRUD |
| `core/chat.py` | You | Swap to RAG chain when course has documents |
| `app.py` | Generated | Wire `upload_view` into the chat page |

---

## Database Change

Add the `documents` table to `init_db()` in `core/database.py`:

```sql
CREATE TABLE IF NOT EXISTS documents (
    id                TEXT PRIMARY KEY,
    course_id         TEXT NOT NULL,
    filename          TEXT NOT NULL,
    file_type         TEXT NOT NULL,       -- pdf | pptx | txt
    document_category TEXT NOT NULL,       -- notes | slides | book | assignment
    source_url        TEXT,
    upload_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chunk_count       INTEGER DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

New CRUD functions needed in `core/database.py`:
- `add_document(course_id, filename, file_type, document_category) -> dict`
- `get_documents(course_id) -> list`
- `update_chunk_count(document_id, count)`
- `delete_document(document_id)`
- `course_has_documents(course_id) -> bool`

---

## core/ingestion.py — What You Will Write

### LangChain concepts

**Document Loaders** — `PyPDFLoader`, `UnstructuredPowerPointLoader`, `TextLoader`

Load a file from disk into a list of LangChain `Document` objects. Each `Document` has:
- `.page_content` — the raw text
- `.metadata` — dict with `source` (filename), `page` (page number), etc.

Why this pattern: loaders normalize different file formats into a single `Document` interface, so the rest of the pipeline doesn't care whether it started as a PDF or a TXT.

**RecursiveCharacterTextSplitter**

Splits documents into overlapping chunks. Use `chunk_size=1000, chunk_overlap=200`.

Why overlap: a concept that spans a chunk boundary won't be silently cut in half. The 200-character overlap ensures context is preserved at seams.

**OpenAIEmbeddings**

Converts each chunk's text into a vector. Similar text → similar vectors (cosine distance). This is what makes semantic search possible.

**Chroma**

Vector database. Each course gets its own collection at `vectorstore/{course_id}/`.

```python
Chroma(
    persist_directory=f"vectorstore/{course_id}",
    embedding_function=OpenAIEmbeddings()
)
```

### Interface to implement

```python
def ingest_file(
    file_path: str,
    course_id: str,
    filename: str,
    file_type: str,           # "pdf" | "pptx" | "txt"
    document_category: str,   # "notes" | "slides" | "book" | "assignment"
    document_id: str,
) -> int:
    """
    Load → split → embed → store in Chroma.
    Returns chunk count.
    Each chunk metadata must include:
      source, page, category, course_id, document_id
    """
```

### Metadata pattern (important)

When you call `text_splitter.split_documents(docs)`, add metadata to each chunk:

```python
for chunk in chunks:
    chunk.metadata["category"] = document_category
    chunk.metadata["course_id"] = course_id
    chunk.metadata["document_id"] = document_id
```

This is what allows category-filtered retrieval later.

---

## core/retrieval.py — What You Will Write

### LangChain concepts

**Chroma as a retriever**

```python
vectorstore.as_retriever(search_kwargs={"k": 4})
```

`k=4` means: return the 4 most similar chunks. You can later add a `filter` kwarg for category filtering.

**RAG chain structure**

```
retriever → RunnableLambda (format context) → ChatPromptTemplate → ChatOpenAI
```

The retrieved `Document` objects need to be formatted into a string before being inserted into the prompt. A simple `RunnableLambda` handles this.

**Why not `RetrievalQA`?** It's a high-level abstraction that hides how context is injected and makes customisation hard. Building the chain manually from primitives teaches you exactly what's happening and gives you full control.

### Interface to implement

```python
def build_rag_chain(course_id: str, system_prompt: str):
    """
    Build and return a RAG chain for the given course.
    The chain accepts {"question": str, "history": list[BaseMessage]}
    and returns a string response with source citations.
    """
```

### Source citation

After retrieval, format context like:

```
[Source: lecture_notes.pdf, page 3]
Processes are programs in execution...

[Source: slides.pdf, page 7]
A deadlock occurs when...
```

The LLM will naturally cite from these tags when answering.

---

## core/chat.py — What You Will Modify

### The change

`get_response()` currently always uses the plain chain. In Milestone 2:
- If the course has documents → use RAG chain from `retrieval.py`
- If not → fall back to plain chain (existing behaviour)

```python
from core import database as db
from core.retrieval import build_rag_chain

def get_response(...):
    ...
    if db.course_has_documents(course_id):
        chain = build_rag_chain(course_id, system_prompt)
    else:
        chain = prompt | model
    ...
```

Note: `get_response()` will need `course_id` added as a parameter.

---

## ui/upload_view.py — Generated

Renders inside the chat view. Contains:
- `st.file_uploader` accepting PDF, PPTX, TXT
- Category selector: Notes / Slides / Book / Assignment
- On upload: save file to `data/courses/{course_id}/uploads/`, call `ingest_file()`, update DB
- Document list showing all uploaded files grouped by category, with a delete button per file

---

## app.py Change — Generated

Wire `render_upload_view(course)` into the chat page, below the chat messages.

---

## Folder Structure After Milestone 2

```
ai_study_assistant/
├── data/
│   └── courses/
│       └── {course_id}/
│           └── uploads/          # saved uploaded files
├── vectorstore/
│   └── {course_id}/              # Chroma collection per course
├── core/
│   ├── ingestion.py              # NEW
│   ├── retrieval.py              # NEW
│   ├── chat.py                   # MODIFIED (RAG switch + course_id param)
│   └── database.py               # MODIFIED (documents table)
└── ui/
    └── upload_view.py            # NEW
```

---

## Implementation Order

1. **Install packages** + update `requirements.txt`
2. **`core/database.py`** — add `documents` table and CRUD (generated for you)
3. **`core/ingestion.py`** — write the ingestion pipeline (you write)
4. **`ui/upload_view.py`** + **`app.py`** wiring (generated) — test file upload and DB entry
5. **`core/retrieval.py`** — write the RAG chain (you write)
6. **`core/chat.py`** — swap chain based on document presence (you write)
7. Manual test against all acceptance criteria

---

## Acceptance Criteria

- [ ] Upload PDF → ask a question → answer cites filename + page number
- [ ] Course A documents do not appear in Course B retrieval
- [ ] Deleting a course removes its `vectorstore/{course_id}/` folder
- [ ] Document list shows all uploaded files per course, grouped by category
- [ ] Course with no documents still works (falls back to plain chain)

---

## Key Decisions Baked In

| Decision | Reason |
|---|---|
| `chunk_size=1000, chunk_overlap=200` | Spec default; balances context window usage vs. retrieval precision |
| Per-course `persist_directory` | Isolation — deleting a course deletes its vector store |
| Manual RAG chain (not `RetrievalQA`) | Teaches the internals; easier to customise for citation formatting |
| `k=4` retrieval | Good default for a 4k context budget; tune up if answers feel incomplete |
| Metadata on every chunk | Enables category filtering in Milestone 3+ without reingesting |
