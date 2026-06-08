# Study Assistant — Project Specification

## Development Philosophy

This project serves two purposes: build a genuinely useful study assistant, and learn LangChain deeply through hands-on implementation.

### Division of Work

**LangChain components — written by me, guided by assistant:**

Chains, prompt templates, retrievers, output parsers, document loaders, embeddings, vector store interactions, memory, runnables.

For these: explain the concept and why this pattern fits before any code is shown. Review my implementation and suggest improvements. Only provide a complete implementation when explicitly requested.

**Everything else — assistant generates directly:**

Streamlit UI, SQLite CRUD, file handling, PDF export, folder management, utility functions, project structure, testing boilerplate.

### Before Introducing Any New LangChain Abstraction

Answer these four questions first:

1. What problem does it solve?
2. Why is it better than the current approach?
3. What are the tradeoffs?
4. Should it be introduced now or postponed?

Do not introduce an abstraction simply because it exists. Prefer the simplest correct implementation that teaches the underlying concept clearly.

### Goal

Not just to finish the project — but to understand every LangChain decision in it.

---

## Vision

A personal AI professor for university studies. Not a generic PDF chatbot.

Each university course gets its own isolated workspace with a dedicated knowledge base, vector store, and conversation history. The assistant teaches using a strict academic format and can generate notes, quizzes, and exam prep material grounded entirely in uploaded course material.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| UI | Streamlit | Already in use, fast to build |
| LLM | GPT-4.1-mini (OpenAI) | Already configured |
| Embeddings | OpenAIEmbeddings | Consistent with LLM provider |
| Vector Store | ChromaDB (per-course) | Already installed, familiar |
| Metadata DB | SQLite | No server needed, file-based |
| PDF Export | fpdf2 | Lightweight, pure Python |
| YouTube | youtube-transcript-api | Already installed |

---

## Folder Structure (Final State)

```
ai_study_assistant/
├── app.py                        # Streamlit entry point
├── .env
├── requirements.txt
├── spec/
│   └── PROJECT_SPEC.md           # This document
├── data/
│   └── courses/
│       └── {course_id}/
│           └── uploads/          # Raw uploaded files
├── vectorstore/
│   └── {course_id}/              # Per-course Chroma collection
├── db/
│   └── study_assistant.db        # SQLite
├── core/
│   ├── __init__.py
│   ├── database.py               # SQLite CRUD (courses, documents, chat)
│   ├── ingestion.py              # Load → split → embed → store
│   ├── retrieval.py              # Per-course RAG chain
│   ├── chat.py                   # Chat chain + history injection
│   ├── teaching.py               # Academic response format + Pydantic models
│   ├── generator.py              # Notes + Quiz structured generation
│   └── exporter.py               # PDF export via fpdf2
└── ui/
    ├── __init__.py
    ├── sidebar.py                # Course list + management
    ├── chat_view.py              # Main chat interface
    └── upload_view.py            # Upload panel
```

---

## Database Schema (Final State)

```sql
CREATE TABLE courses (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    course_prompt TEXT,          -- custom instructions per course (e.g. "Answer in FLAME exam style")
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id                TEXT PRIMARY KEY,
    course_id         TEXT NOT NULL,
    filename          TEXT NOT NULL,
    file_type         TEXT NOT NULL,       -- pdf | pptx | txt | youtube
    document_category TEXT NOT NULL,       -- notes | slides | book | assignment | youtube
    source_url        TEXT,                -- YouTube URL if applicable
    upload_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chunk_count       INTEGER DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE chat_messages (
    id        TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    role      TEXT NOT NULL,     -- human | ai
    content   TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

---

## Teaching Philosophy (Default Behavior)

For every academic question, the response follows this format unless the user explicitly requests otherwise:

1. **Repeat full question** — exact wording
2. **Professor explanation** — precise, technical
3. **Beginner explanation** — plain language
4. **Analogy** — real-world comparison when possible
5. **Theory & concepts** — definitions, formulas, rules
6. **Worked examples** — step-by-step
7. **Common mistakes** — what students typically get wrong
8. **Practice questions** — exam-style
9. **Model answers** — full exam-format answers

Encoded as a system prompt + `AcademicResponse` Pydantic model.

---

## Milestones

---

### Milestone 1 — Course Shell + Basic Chat (MVP)

**Goal:** Working app with course management and plain LLM chat. No RAG yet.

**Features:**
- Create / rename / delete courses
- Course-specific custom instructions (`course_prompt`) — e.g. "Answer in FLAME University exam style" or "Focus on mathematical derivations"
- Course list in sidebar
- Per-course chat with persisted history (SQLite)
- Teaching philosophy baked into system prompt; `course_prompt` appended on top
- ChatGPT-style UI: sidebar + main chat + input at bottom

**LangChain concepts:**
- `ChatPromptTemplate` + `MessagesPlaceholder`
- `ChatOpenAI`
- Manual history injection from SQLite (`HumanMessage` / `AIMessage` lists)
- Note: `RunnableWithMessageHistory` is the proper LangChain abstraction for this — adopt it in a later refactor once the basic flow is stable

**Files:**
- `app.py` — Streamlit shell, routing between sidebar and chat
- `core/database.py` — CRUD for courses and chat_messages
- `core/chat.py` — system prompt + course_prompt + history + user message → LLM
- `ui/sidebar.py` — course list, create/rename/delete, edit course instructions
- `ui/chat_view.py` — message rendering, input box

**DB changes:** `courses` (with `course_prompt`) + `chat_messages` tables created on first run.

**UI:**
- Sidebar: course list + "+ New Course" button + rename/delete per course
- Main: messages top-to-bottom, input box pinned at bottom

**Acceptance criteria:**
- [ ] Create, rename, delete a course
- [ ] Switching courses switches chat history
- [ ] Chat history survives app restart
- [ ] Default responses follow the 9-step academic format
- [ ] Deleting a course deletes its chat history

---

### Milestone 2 — Knowledge Base + RAG

**Goal:** Upload documents to a course, answer questions with source citations.

**Features:**
- Upload: PDF, PPTX, TXT, DOCX
- Each upload assigned a `document_category`: `notes`, `slides`, `book`, `assignment`
- Per-course ChromaDB vector store
- RAG chain replaces plain LLM chain
- Source citations in responses (filename + page number)
- Category-filtered retrieval: "search only slides", "search only book" becomes possible
- Document list visible per course, grouped by category

**LangChain concepts:**
- `PyPDFLoader`, `UnstructuredPowerPointLoader`, `TextLoader`
- `RecursiveCharacterTextSplitter` — default: **chunk_size=1000, chunk_overlap=200**
- `OpenAIEmbeddings`
- `Chroma(persist_directory="vectorstore/{course_id}")`
- Custom RAG chain: retriever → context injection → prompt → LLM
- Document metadata stored per chunk: `{"source": filename, "page": n, "category": document_category, "course_id": course_id}`
- Category filter passed as Chroma `where` clause: `{"category": "slides"}`

**Files:**
- `core/ingestion.py` — file → load → split → embed → Chroma
- `core/retrieval.py` — build retriever for active course, build RAG chain
- `core/chat.py` — use RAG chain when course has documents, plain chain otherwise
- `ui/upload_view.py` — file uploader widget + document list

**DB changes:** `documents` table added.

**UI:** 📎 popover button in the chat header (top-right). Upload form + document list live inside the popover. Toast notification on successful upload. Chat flow is uninterrupted — the upload UI never sits between messages and the input box.

**Acceptance criteria:**
- [ ] Upload PDF → ask question → answer cites filename + page
- [ ] Course A documents do not appear in Course B retrieval
- [ ] Deleting a course removes its `vectorstore/{course_id}/` folder
- [ ] Document list shows all uploaded files per course

---

### Milestone 3 — YouTube Lecture Support

**Goal:** Add YouTube lecture URLs to the course knowledge base.

**Features:**
- Paste YouTube URL into upload area
- Transcript extracted and indexed in course vector store
- Citable as a source like any uploaded document

**LangChain concepts:**
- `YoutubeLoader` from `langchain_community.document_loaders`
- Plugs into the existing ingestion pipeline unchanged

**Files:**
- `core/ingestion.py` — add `ingest_youtube(url, course_id)` branch
- `ui/upload_view.py` — URL input field alongside file uploader

**DB changes:** `documents` row with `file_type='youtube'`, `document_category='youtube'`, and `source_url` set.

**Known failure mode:** `youtube-transcript-api` requires captions to be enabled on the video. Auto-generated captions work on most English videos but can be unavailable for non-English content or manually disabled channels. Show a specific error: *"No transcript available for this video. Try a different lecture or check if captions are enabled."*

**Acceptance criteria:**
- [ ] Paste YouTube URL → transcript indexed in ~30s
- [ ] Ask question answered from video content → source shows video title
- [ ] Invalid URL shows a clear error message
- [ ] Video with no captions shows a specific, helpful error (not a stack trace)

---

### Milestone 4 — Structured Academic Responses

**Goal:** Enforce the 9-step teaching format as structured Pydantic output with clean rendering.

**Features:**
- `AcademicResponse` Pydantic model (9 fields)
- Mode toggle: "Academic" (default) vs "Quick Answer"
- Each section rendered with its own heading in the chat

**LangChain concepts:**
- `PydanticOutputParser` with `AcademicResponse`
- Updated RAG chain: retriever → context → structured prompt → LLM → parser
- `RunnableParallel` (optional, for parallel section generation)

**Pydantic model:**

> **Design note:** Do not use parallel `list[str]` for `practice_questions` and `model_answers` — if index 0 of one doesn't align with index 0 of the other the output silently breaks. Use a `QAPair` object instead.

```python
class QAPair(BaseModel):
    question: str
    answer: str

class AcademicResponse(BaseModel):
    question_repeated: str
    professor_explanation: str
    beginner_explanation: str
    analogy: Optional[str]
    theory_and_concepts: str
    worked_examples: str
    common_mistakes: Optional[str]
    practice_questions: list[QAPair]   # question + answer always travel together
```

**Files:**
- `core/teaching.py` — `AcademicResponse` model + structured prompt template
- `core/chat.py` — swap parser based on mode flag
- `ui/chat_view.py` — render each section with a heading

**Acceptance criteria:**
- [ ] Academic mode shows all 9 sections with headings
- [ ] Quick mode returns plain prose
- [ ] Mode toggle persists within the session
- [ ] Optional fields (analogy, common_mistakes) render only when present

---

### Milestone 5 — Notes & Quiz Generation

**Goal:** Generate structured study materials from course content. Export as PDF.

**Note types:** Detailed Notes, Revision Notes, Exam Notes, Cheat Sheet

**Quiz types:** MCQ (with answer + explanation), Short Answer, Long Answer, Viva Questions

**Flashcards:** Front (concept/term) + Back (definition/explanation). High-value study tool. Generate a deck for any topic.

**LangChain concepts:**
- `PydanticOutputParser` for `NoteDocument` and `QuizDocument`
- RAG retrieval grounding generation in uploaded material
- `RunnableParallel` for multi-section note generation

**Pydantic models:**
```python
class NoteSection(BaseModel):
    heading: str
    content: str

class NoteDocument(BaseModel):
    title: str
    sections: list[NoteSection]

class MCQQuestion(BaseModel):
    question: str
    options: list[str]   # 4 options
    correct: str
    explanation: str

class QuizDocument(BaseModel):
    title: str
    questions: list[MCQQuestion]

class Flashcard(BaseModel):
    front: str    # concept, term, or question
    back: str     # definition, explanation, or answer

class FlashcardDeck(BaseModel):
    title: str
    cards: list[Flashcard]
```

**Files:**
- `core/generator.py` — `generate_notes(...)`, `generate_quiz(...)`, `generate_flashcards(topic, course_id)`
- `core/exporter.py` — `export_to_pdf(document)` using fpdf2
- `ui/chat_view.py` — Generate buttons + rendered output + download button

**fpdf2 scope:** Keep it conservative. Support: title, headings, body paragraphs, numbered lists, bullet points. Do **not** attempt tables, math notation, or code blocks in PDF — render those in-chat only. Scope creep here wastes significant time.

**Acceptance criteria:**
- [ ] Generate MCQ quiz on any topic → download as PDF
- [ ] Generate flashcard deck → displayed as flippable cards in UI
- [ ] Revision notes grounded in uploaded material, not hallucinated
- [ ] PDF covers title, headings, and body text cleanly
- [ ] Cheat sheet is dense, bullet-pointed, one column

---

### Milestone 6 — Exam Preparation Mode

**Goal:** Course-aware exam preparation: important questions, predicted questions, full practice papers.

**Features:**
- Important questions extracted from uploaded material
- Predicted questions based on topic coverage
- Full model answers in exam format
- Complete practice paper with sections (MCQ / Short / Long) and marks

**LangChain concepts:**
- High-k RAG retrieval (top 10–15 chunks) for topic coverage analysis
- Structured output for `PracticePaper` model
- Reuses `generator.py` and `exporter.py` from Milestone 5

**Pydantic model:**
```python
class ExamQuestion(BaseModel):
    question: str
    marks: int
    model_answer: str

class PaperSection(BaseModel):
    section_name: str
    instructions: str
    questions: list[ExamQuestion]

class PracticePaper(BaseModel):
    course_name: str
    sections: list[PaperSection]
```

**Files:**
- `core/generator.py` — add `generate_practice_paper(course_id, instructions)`
- `ui/chat_view.py` — Exam Prep button group

**Acceptance criteria:**
- [ ] Generate full practice paper for any course in under 30s
- [ ] Paper has at least 3 sections with marks assigned
- [ ] Every question has a full model answer
- [ ] Paper exports as clean PDF

---

### Milestone 7 — Semantic Search Page

**Goal:** A dedicated search interface — Google for your course material.

**Features:**
- Search bar (separate from chat)
- Returns ranked chunks from all course documents
- Results show: document name, category, page number, and a text excerpt
- Optional: filter by category (slides only, book only, etc.)

This is different from chat. No LLM involved — pure vector similarity search. Fast and transparent.

**LangChain concepts:**
- `Chroma.similarity_search_with_score(query, k=10, filter={"course_id": ...})`
- Optional category filter: `filter={"category": "slides"}`

**Files:**
- `ui/search_view.py` — search input + results list
- `core/retrieval.py` — add `semantic_search(query, course_id, category=None, k=10)`

**UI:** New tab or sidebar link: "Search". Shows results as cards with source info.

**Acceptance criteria:**
- [ ] Type "deadlock" → see ranked results from all course documents
- [ ] Each result shows: filename, category, page, excerpt
- [ ] Filter by category works (e.g. slides only)
- [ ] Empty course shows helpful empty state

---

## Implementation Order (per milestone)

1. Core logic in `core/` — no UI dependency
2. DB schema changes
3. UI integration
4. Manual test: `streamlit run app.py` → verify acceptance criteria

---

## UI Principles

1. Chat is the primary feature — it must occupy ~80% of visible space.
2. Chat input stays fixed at the bottom; nothing should push it downward.
3. File upload never sits in the middle of the conversation flow.
4. Knowledge base management lives in a popover or collapsible — closed by default.
5. Success notifications use `st.toast()` (compact, auto-hides) not `st.success()` banners.
6. Course management and file management are secondary — sidebar or popover only.

---

## Out of Scope

- User authentication (single-user local app)
- Cloud deployment
- Video file uploads (YouTube transcript only)
- Non-OpenAI LLMs (swap `ChatOpenAI` later if needed)
- Real-time collaboration
