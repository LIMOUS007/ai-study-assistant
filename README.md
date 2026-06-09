# AI Study Assistant

A personal AI professor for university studies. Each course gets its own isolated workspace with a dedicated knowledge base, vector store, and chat history. The assistant teaches using a structured academic format and can generate notes, quizzes, flashcards, practice papers, and two-column LaTeX exam notes grounded entirely in your uploaded course material.

Built with LangChain, Streamlit, ChromaDB, and HuggingFace embeddings.

---

## Features

### Course Management
- Create, rename, and delete courses
- Per-course custom instructions (e.g. "Answer in FLAME University exam style" or "Focus on mathematical proofs")
- Chat history persists between sessions, isolated per course
- Courses sorted by most recently used

### Knowledge Base (RAG)
- Upload **PDF, PPTX, DOCX, and TXT** files to any course
- Add **YouTube lecture URLs** — transcripts are auto-fetched and indexed
- Paste or type notes directly via the text tab
- Per-course ChromaDB vector store with source citations (filename + page number)
- Documents organised by category: Notes, Slides, Book, Assignment
- Delete individual documents or clear the entire knowledge base

### Two Chat Modes
- **Academic mode** (default) — structured 9-section format: question repeated, professor explanation, plain-language explanation, analogy, theory & concepts, worked examples, common mistakes, practice questions with model answers
- **Quick Answer mode** — natural prose, like a lecture conversation

### Study Material Generation
All generators retrieve context from your uploaded course material via semantic search.

- **Notes** — four styles: Detailed, Revision, Exam, Cheat Sheet
- **Quiz** — MCQ with 4 options, correct answer, and explanation; balanced question type mix (recall, trace, complexity, comparison, application)
- **Flashcards** — interactive flip-card UI; balanced card type mix (definition, complexity, pattern, comparison, pitfall, trace)
- **Practice Paper** — full exam paper with Section A (MCQ), B (short answer), C (long answer) and complete model answers
- **Exam-Ready Notes (LaTeX)** — two-column LaTeX document with syntax-highlighted code blocks, exam callouts, pattern recognition boxes, ASCII diagrams, and complexity tables; opens directly in Overleaf or downloads as `.tex`

Compound topics auto-expand into individual generation calls for thorough coverage:
- `"Sorting"` → Bubble, Selection, Insertion, Quick, Merge (5 calls)
- `"Linked Lists"` → SLL, DLL (2 calls)
- `"Stacks"` → Operations, Applications (2 calls)
- `"Trees"`, `"Graphs"`, `"Hashing"`, `"Recursion"` → 2–4 calls each

### Semantic Search
- Query your uploaded material by semantic similarity — no keywords needed
- Filter results by document category
- Relevance scores shown per result

### Multiple AI Providers
Switch providers from the sidebar. Status is auto-tested on first load.

| Provider | Model | Notes |
|---|---|---|
| Cerebras | gpt-oss-120b | Default — fastest, free tier available |
| OpenAI | gpt-4.1-mini | Requires paid credits |
| Google | gemini-2.5-flash | Requires API key |
| Groq | llama-3.3-70b | Requires API key |

---

## Tech Stack

| Layer | Choice |
|---|---|
| UI | Streamlit |
| LLM | Cerebras / OpenAI / Google Gemini / Groq — via LangChain |
| Embeddings | HuggingFace `sentence-transformers/all-MiniLM-L6-v2` (local, free) |
| Vector Store | ChromaDB (per-course, persistent) |
| Metadata DB | SQLite |
| PDF Export | fpdf2 |
| LaTeX Compile | latex.vercel.app / YtoTech / TeXLive.net (remote, tries in order) |
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

### 3. Add your API keys

Create a `.env` file in the project root. You only need keys for the providers you want to use — Cerebras is free and recommended as a starting point.

```
CEREBRAS_API_KEY=csk-...
OPENAI_API_KEY=sk-...          # optional
GOOGLE_API_KEY=...             # optional
groq_api_key=gsk_...           # optional
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
├── app.py                    # Streamlit entry point
├── requirements.txt
├── .env                      # API keys (not committed)
├── core/
│   ├── database.py           # SQLite CRUD — courses, documents, chat messages
│   ├── ingestion.py          # File/YouTube -> split -> embed -> ChromaDB
│   ├── retrieval.py          # RAG chains (plain and academic) with relevance filtering
│   ├── chat.py               # Chat entry point — picks chain based on mode and docs
│   ├── teaching.py           # AcademicResponse Pydantic model + prompt + markdown renderer
│   ├── generator.py          # Notes, Quiz, Flashcard, Practice Paper, LaTeX generation
│   ├── exporter.py           # PDF export (fpdf2) and LaTeX source builder
│   └── llm.py                # Provider registry, get_model(), check_api_key(), UsageTracker
├── ui/
│   ├── sidebar.py            # Course list, create/rename/delete, mode toggle, provider switcher
│   ├── chat_view.py          # Chat interface + Generate tab + result renderers
│   ├── upload_view.py        # File uploader, YouTube URL, paste-text tab, document list
│   └── search_view.py        # Semantic search UI
├── tests/
│   ├── test_database.py
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_course_delete.py
│   ├── test_exporter.py
│   ├── test_generator.py
│   ├── test_llm.py
│   └── test_teaching.py
├── data/
│   └── courses/{id}/uploads/ # Raw uploaded files (git-ignored)
├── vectorstore/
│   └── {course_id}/          # Per-course Chroma store (git-ignored)
└── db/
    └── study_assistant.db    # SQLite (git-ignored)
```

---

## Running Tests

```bash
venv\Scripts\python -m pytest tests/ -v
```

146 tests covering database CRUD, ingestion, retrieval formatting, export (PDF + LaTeX), LLM key checker, teaching response rendering, and generator topic expansion logic.

---

## LangChain Concepts Used

| Concept | Where |
|---|---|
| `ChatPromptTemplate` + `MessagesPlaceholder` | `core/chat.py`, `core/retrieval.py`, `core/teaching.py` |
| `ChatOpenAI`, `ChatGoogleGenerativeAI`, `ChatGroq` | `core/llm.py` |
| `HumanMessage` / `AIMessage` | Chat history in `core/chat.py` |
| `PyPDFLoader`, `TextLoader`, `Docx2txtLoader` | `core/ingestion.py` |
| `RecursiveCharacterTextSplitter` | `core/ingestion.py` |
| `HuggingFaceEmbeddings` | `core/ingestion.py`, `core/retrieval.py`, `core/generator.py` |
| `Chroma` (PersistentClient) | `core/ingestion.py`, `core/retrieval.py`, `core/generator.py` |
| `.with_structured_output(PydanticModel)` | `core/generator.py` — notes, quiz, flashcards, LaTeX |
| `PydanticOutputParser` | `core/teaching.py` — academic response format |
| `RunnableLambda` | RAG chains in `core/retrieval.py` |
| `StrOutputParser` | Plain fallback chains |
| `BaseCallbackHandler` | `UsageTracker` in `core/llm.py` |

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
    file_type         TEXT NOT NULL,       -- pdf | pptx | docx | txt | youtube
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

- Deleting a course removes its vector store, uploaded files, and all chat history.
- YouTube indexing requires captions to be enabled on the video. Auto-generated captions work for most English videos.
- The app disables SSL verification globally — required on networks with SSL inspection (e.g. university proxies). Remove the `verify=False` patches at the top of `app.py` if not needed.
- Generated PDFs strip markdown and code blocks (plain text only). Use the LaTeX export for code-heavy content.
- Cerebras free tier rate-limits after a few rapid back-to-back calls. If you see a 429 error, wait a few seconds and retry.
- The HuggingFace embedding model (`all-MiniLM-L6-v2`) downloads ~90 MB on first run and is cached locally. No API key required.
