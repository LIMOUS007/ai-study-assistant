# Milestone 4 — Structured Academic Responses

## Goal

Replace the prose teaching-philosophy prompt with a `PydanticOutputParser`-enforced 9-section academic format. Add a mode toggle so the user can switch between "Academic" (structured, more tokens) and "Quick Answer" (plain prose, cheaper). Sections render as flowing markdown — no clinical labels like "Professor Explanation:".

---

## How PydanticOutputParser Works (Concept First)

### Problem it solves

Right now the LLM is asked to write in a specific style via the system prompt. It usually does — but it's free-form text. There's no way to reliably detect whether the analogy or common-mistakes section was included or silently omitted.

`PydanticOutputParser` solves this by asking the LLM to return structured JSON that maps to a Pydantic model. LangChain auto-generates the JSON schema instructions and appends them to the prompt. After the LLM responds, the parser deserializes the JSON into a Python object — so optional fields that the LLM omitted come back as `None`, not a missing substring.

### Why it matters beyond this milestone

M5 (Notes & Quiz generation) uses the exact same pattern with `NoteDocument` and `QuizDocument`. Learning `PydanticOutputParser` in M4 means M5 is straightforward.

### The tradeoff

The LLM must output a complete, valid JSON object. This costs more tokens than prose — which is why the mode toggle exists. "Quick Answer" skips the parser and uses `StrOutputParser` as before.

### How it plugs into the chain

```
retriever → format_docs → prompt (with format_instructions appended) → LLM → PydanticOutputParser → AcademicResponse
```

The `PydanticOutputParser` adds `{format_instructions}` to the prompt — a JSON schema block that tells the LLM exactly what to output.

```python
parser = PydanticOutputParser(pydantic_object=AcademicResponse)
format_instructions = parser.get_format_instructions()
# inject into system message: "...\n\n{format_instructions}"
# at parse time: parser.parse(llm_output) → AcademicResponse object
```

---

## Packages — No New Installs Needed

`pydantic` is already a transitive dependency. `PydanticOutputParser` is in `langchain_core.output_parsers`.

---

## Files

### New

| File | Written by | Purpose |
|---|---|---|
| `core/teaching.py` | You | `QAPair`, `AcademicResponse` models + parser + academic prompt template |

### Modified

| File | Written by | Change |
|---|---|---|
| `core/retrieval.py` | You | Add `build_academic_rag_chain()` using `PydanticOutputParser` |
| `core/chat.py` | You | Add `mode` param; route to correct chain |
| `ui/chat_view.py` | Generated | Mode toggle; flowing section rendering |

---

## core/teaching.py — What You Will Write

### LangChain concepts

**`PydanticOutputParser`** — wraps a Pydantic `BaseModel`. Adds a `{format_instructions}` variable you inject into the prompt. After the LLM responds with JSON, call `parser.parse(llm_string_output)` to get a typed Python object back.

**`Optional` fields** — `analogy` and `common_mistakes` are `Optional[str]`. The parser will set them to `None` if the LLM omits them. The rendering code checks for `None` and silently skips those blocks — no guessing whether the LLM included it or not.

> **Design note:** Do not use parallel `list[str]` for `practice_questions` and `model_answers`. If index 0 of one doesn't align with index 0 of the other, the output silently breaks. Use a `QAPair` object so question and answer always travel together.

### Models to implement

```python
from pydantic import BaseModel
from typing import Optional

class QAPair(BaseModel):
    question: str
    answer: str

class AcademicResponse(BaseModel):
    question_repeated: str
    professor_explanation: str
    beginner_explanation: str
    analogy: Optional[str] = None
    theory_and_concepts: str
    worked_examples: str
    common_mistakes: Optional[str] = None
    practice_questions: list[QAPair]
```

### Interface to implement

```python
def get_academic_parser() -> PydanticOutputParser:
    """Return a PydanticOutputParser wrapping AcademicResponse."""

def build_academic_prompt(system_prompt: str) -> ChatPromptTemplate:
    """
    Build the prompt template for structured academic output.
    The system message must include {format_instructions} so the parser
    can inject the JSON schema. Also include {context} for RAG injection.
    Structure:
      - system: system_prompt + academic teaching instruction + {context} + {format_instructions}
      - history: MessagesPlaceholder
      - human: {question}
    """
```

The teaching instruction in the system message should enumerate all 9 sections and instruct the LLM to populate every field. The `{format_instructions}` block tells it to output valid JSON.

### Helper (generated — you don't need to write this)

`academic_response_to_markdown(response: AcademicResponse) -> str` — flattens an `AcademicResponse` into flowing markdown for saving to the DB. Sections are separated by `---` rather than labeled headers. Optional fields are omitted when `None`.

---

## core/retrieval.py — What You Will Modify

### New function to add

```python
def build_academic_rag_chain(course_id: str, system_prompt: str):
    """
    Build a RAG chain for Academic mode. Returns a string (flattened markdown).

    Pipeline:
      retriever → _format_docs → build_academic_prompt → LLM → PydanticOutputParser → flatten to markdown

    Uses the same retriever setup as build_rag_chain (same vectorstore path,
    same k=4, same _format_docs and _unique_sources helpers). The only differences:
      - prompt comes from teaching.build_academic_prompt()
      - StrOutputParser is replaced by PydanticOutputParser(AcademicResponse)
      - the parsed AcademicResponse is flattened to markdown via academic_response_to_markdown()
        before returning, so the caller receives a string in both modes
    """
```

### Why return a string (not AcademicResponse)?

The rendering in `chat_view.py` uses `st.markdown()` in both modes. Keeping the return type as `str` in both modes means `chat.py` and `chat_view.py` don't need branching logic — they handle a string either way. The structured parsing happens inside the chain, and its value is the **reliability guarantee** (all 9 sections present, optional fields detected) plus the **learning goal** — not a different runtime type.

Sources are appended to the flattened markdown string the same way as Quick mode.

---

## core/chat.py — What You Will Modify

### Updated `get_response` signature

```python
def get_response(
    user_message: str,
    course_name: str,
    course_prompt: str,
    chat_history: list,
    course_id: str,
    mode: str = "academic",    # "academic" | "quick"
) -> str:
```

Dispatch logic:
- `mode="quick"` and no documents → plain chain (existing)
- `mode="quick"` and has documents → `build_rag_chain()` (existing)
- `mode="academic"` and no documents → plain academic chain (no retriever, context = `""`)
- `mode="academic"` and has documents → `build_academic_rag_chain()` (new)

The return type stays `str` in all cases — no change needed in `chat_view.py`'s existing save-to-DB logic.

---

## ui/chat_view.py — Generated

### Mode toggle

A compact `st.radio` in the chat header:

```
Mode:  ● Academic   ○ Quick Answer
```

Stored in `st.session_state["chat_mode"]`, defaulting to `"academic"`. Changing mode takes effect on the next message — it does not re-run the previous response.

### Rendering

Both modes render via `st.markdown(response)` — no branching needed in the UI since the chain returns a string in both cases. Academic mode responses will naturally have `---` separators between sections (from `academic_response_to_markdown`); Quick mode returns plain prose.

---

## DB Changes

None. `chat_messages` table is unchanged. Academic mode responses are saved as flattened markdown strings, same as Quick mode.

---

## Implementation Order

1. **`core/teaching.py`** — write `QAPair`, `AcademicResponse`, `get_academic_parser()`, `build_academic_prompt()`. Test: instantiate the parser, call `get_format_instructions()`, confirm it produces a valid JSON schema string.
2. **`core/retrieval.py`** — add `build_academic_rag_chain()`. Test: call it, send a question, confirm you get back a markdown string with all 9 sections present.
3. **`core/chat.py`** — update `get_response()` signature and dispatch.
4. **`ui/chat_view.py`** — generated: mode toggle wired to `st.session_state["chat_mode"]`.
5. Manual test: `streamlit run app.py` → verify all acceptance criteria.

---

## Acceptance Criteria

- [ ] Academic mode response contains all 9 sections (no labeled headers — flowing markdown)
- [ ] Quick mode returns plain prose (existing behaviour, no regression)
- [ ] Mode toggle persists within the session
- [ ] Optional fields (analogy, common_mistakes) are silently omitted when the LLM returns `None`
- [ ] Academic mode works for courses with no documents (plain LLM, no retriever)
- [ ] Both modes save correctly to chat history and survive app restart

---

## Key Decisions

| Decision | Reason |
|---|---|
| `PydanticOutputParser` over structured markdown prompt | Learning goal; optional-field detection without string heuristics; prepares for M5 Notes/Quiz |
| `QAPair` instead of parallel `list[str]` | Question and answer always travel together; no silent index misalignment |
| Return `str` from both chains | No branching in `chat_view.py`; structured parsing is an implementation detail, not a UI concern |
| Flatten to markdown with `---` separators, no labels | Matches the project's "conversational, not form-like" philosophy |
| Mode toggle kept, Explain Again buttons removed | Toggle is low complexity and justifies the token cost difference; Explain Again added unnecessary session state management |
| No new DB columns | M4 is pure chain/UI work; schema is stable from M3 |
