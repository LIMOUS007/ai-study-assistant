# AI Study Assistant

A personal AI professor for university studies. Each course gets its own isolated workspace with a dedicated knowledge base, vector store, and chat history. The assistant teaches using a structured academic format and can generate notes, quizzes, flashcards, and exam prep material grounded entirely in your uploaded course material.

Built with LangChain, Streamlit, ChromaDB, and OpenAI.

---

## Features

### Course Management
- Create, rename, and delete courses
- Per-course custom instructions (e.g. "Answer in FLAME University exam style" or "Focus on mathematical derivations")
- Chat history persists between sessions, isolated per course

### Knowledge Base (RAG)
- Upload PDF, DOCX, and TXT files to any course
- Add YouTube lecture URLs — transcripts are auto-fetched and indexed
- Per-course ChromaDB vector store with source citations (filename + page number)
- Documents organised by category: Notes, Slides, Book, Assignment

### Two Response Modes
- **Academic mode** (default) — structured 9-section format: question repeated, professor explanation, plain-language explanation, analogy, theory & concepts, worked examples, common mistakes, practice questions with model answers
- **Quick Answer mode** — natural prose, like a lecture conversation

### Study Material Generation
- **Notes** — Detailed, Revision, Exam, or Cheat Sheet style, grounded in uploaded material
- **Quiz** — MCQ with 4 options, correct answer, and explanation per question
- **Flashcards** — flippable card UI with front (concept) and back (definition/answer)
- All outputs downloadable as PDF

---

## Tech Stack

| Layer | Choice |
|---|---|
| UI | Streamlit |
| LLM | GPT-4.1-mini (OpenAI) |
| Embeddings | OpenAI text-embedding-ada-002 |
| Vector Store | ChromaDB (per-course, persistent) |
| Metadata DB | SQLite |
| PDF Export | fpdf2 |
| YouTube | youtube-transcript-api |

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd ai_study_assistant
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your OpenAI API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

### 4. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Project Structure

```
ai_study_assistant/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── .env                    # API key (not committed)
├── core/
│   ├── database.py         # SQLite CRUD — courses, documents, chat messages
│   ├── ingestion.py        # File/YouTube → split → embed → ChromaDB
│   ├── retrieval.py        # RAG chains (plain and academic) with relevance filtering
│   ├── chat.py             # Main chat entry point — picks chain based on mode and docs
│   ├── teaching.py         # AcademicResponse Pydantic model + prompt + markdown renderer
│   ├── generator.py        # Notes, Quiz, Flashcard generation with PydanticOutputParser
│   └── exporter.py         # PDF export via fpdf2
├── ui/
│   ├── sidebar.py          # Course list, create/rename/delete, response mode toggle
│   ├── chat_view.py        # Chat interface + Generate tab
│   └── upload_view.py      # File uploader + YouTube URL + document list
├── data/
│   └── courses/{id}/uploads/   # Raw uploaded files (git-ignored)
├── vectorstore/
│   └── {course_id}/            # Per-course Chroma store (git-ignored)
└── db/
    └── study_assistant.db      # SQLite (git-ignored)
```

---

## LangChain Concepts Used

| Concept | Where |
|---|---|
| `ChatPromptTemplate` + `MessagesPlaceholder` | `core/chat.py`, `core/retrieval.py` |
| `ChatOpenAI` | All LLM calls |
| `HumanMessage` / `AIMessage` | Chat history injection in `core/chat.py` |
| `PyPDFLoader`, `TextLoader`, `Docx2txtLoader` | `core/ingestion.py` |
| `RecursiveCharacterTextSplitter` | `core/ingestion.py` |
| `OpenAIEmbeddings` | `core/ingestion.py`, `core/retrieval.py` |
| `Chroma` (PersistentClient) | `core/ingestion.py`, `core/retrieval.py`, `core/generator.py` |
| `PydanticOutputParser` | `core/teaching.py`, `core/generator.py` |
| `RunnableLambda` | RAG chains in `core/retrieval.py` |
| `StrOutputParser` | Plain fallback chains |

---

## Database Schema

```sql
CREATE TABLE courses (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    course_prompt TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id                TEXT PRIMARY KEY,
    course_id         TEXT NOT NULL,
    filename          TEXT NOT NULL,
    file_type         TEXT NOT NULL,       -- pdf | docx | txt | youtube
    document_category TEXT NOT NULL,       -- notes | slides | book | assignment | youtube
    source_url        TEXT,
    upload_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chunk_count       INTEGER DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE chat_messages (
    id        TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    role      TEXT NOT NULL,               -- human | ai
    content   TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

---

## Notes

- Deleting a course removes its vector store folder and all chat history.
- YouTube indexing requires captions to be enabled on the video. Auto-generated captions work for most English videos.
- The app disables SSL verification (`verify=False`) for OpenAI and embedding calls — required on networks with SSL inspection (e.g. university proxies). Remove `http_client=httpx.Client(verify=False)` if not needed.
- Generated PDFs support plain text only — code blocks are replaced with a placeholder, markdown formatting is stripped.
