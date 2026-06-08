from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb, httpx
from pathlib import Path


# ─── MODELS ───────────────────────────────────────────────────────────────────

class NoteSection(BaseModel):
    heading: str
    content: str

class NoteDocument(BaseModel):
    title: str
    sections: list[NoteSection]

class MCQQuestion(BaseModel):
    question: str
    options: list[str]   # exactly 4
    correct: str         # must match one of options exactly
    explanation: str

class QuizDocument(BaseModel):
    title: str
    questions: list[MCQQuestion]

class Flashcard(BaseModel):
    front: str
    back: str

class FlashcardDeck(BaseModel):
    title: str
    cards: list[Flashcard]

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


# ─── HELPER ───────────────────────────────────────────────────────────────────

def retrieve_context(topic: str, course_id: str, k: int = 6) -> str:
    vectorstore_path = Path("vectorstore") / course_id
    # embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    vector_store = Chroma(client=client, embedding_function=embeddings)
    docs = vector_store.similarity_search(topic, k=k)
    if not docs:
        return ""
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        page_str = f", page {page}" if page != "" else ""
        parts.append(f"[Source: {source}{page_str}]\n{doc.page_content}")
    return "\n\n".join(parts)


# ─── GENERATORS ───────────────────────────────────────────────────────────────

def generate_notes(topic: str, note_type: str, course_id: str) -> NoteDocument:
    context = retrieve_context(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")

    parser = PydanticOutputParser(pydantic_object=NoteDocument)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor writing open-book university exam notes. "
         "Write like a textbook, not a blog. Be dense, precise, and academic.\n\n"
         "STRUCTURE:\n"
         "- Use hierarchical numbered sections: '1 Topic', '1.1 Subtopic', '1.2 Subtopic'\n"
         "- Each new concept: definition → core idea → why it matters → complexity if applicable\n\n"
         "CALLOUTS — include naturally throughout:\n"
         "- 'Exam move:' — technique or insight that scores marks\n"
         "- 'Pitfall:' — common error and how to avoid it\n"
         "- 'Common mistake:' — what students typically get wrong\n\n"
         "WORKED EXAMPLES — after every major concept:\n"
         "- State the problem, give high-level reasoning, trace execution step-by-step on real input, "
         "then show the full correct code (not pseudocode), end with Time/Space complexity.\n\n"
         "END OF NOTES: one tight summary section — key patterns, common exam questions, "
         "or fast-revision checklist, whichever fits best.\n\n"
         "DEPTH — adapt based on note_type='{note_type}':\n"
         "- detailed: everything above, fully elaborated, multiple examples per concept\n"
         "- revision: key definitions + one example per concept, skip deep theory\n"
         "- exam: callouts, patterns, complexity tables, summary only — no prose\n"
         "- cheat_sheet: bullet points only, no prose, no full code, maximum density\n\n"
         "Topic to cover: {topic}\n\n"
         "Use ONLY the course material below. Do not use outside knowledge.\n"
         "{context}\n\n"
         "{format_instructions}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    chain = prompt | model | parser
    return chain.invoke({
        "topic": topic,
        "note_type": note_type,
        "context": context,
        "format_instructions": format_instructions,
    })


def generate_quiz(topic: str, quiz_type: str, course_id: str, num_questions: int = 5) -> QuizDocument:
    context = retrieve_context(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")

    parser = PydanticOutputParser(pydantic_object=QuizDocument)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor writing an exam-style MCQ quiz.\n\n"
         "Generate exactly {num_questions} MCQ questions on the topic: {topic}\n\n"
         "RULES:\n"
         "- Use ONLY the course material provided below. Do not use outside knowledge.\n"
         "- Each question must have exactly 4 options written as full sentences, not letters.\n"
         "- The 'correct' field must be copied EXACTLY from one of the options — "
         "not 'A', not 'option 1', the full string verbatim.\n"
         "- Each question needs a clear explanation of why the correct answer is right "
         "and why the others are wrong.\n"
         "- Questions must be exam-style difficulty — no trivial or obvious questions.\n"
         "- Cover different parts of the material, not the same concept repeatedly.\n\n"
         "Course material:\n{context}\n\n"
         "{format_instructions}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    chain = prompt | model | parser
    return chain.invoke({
        "topic": topic,
        "num_questions": num_questions,
        "context": context,
        "format_instructions": format_instructions,
    })


def generate_flashcards(topic: str, course_id: str, num_cards: int = 10) -> FlashcardDeck:
    context = retrieve_context(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")

    parser = PydanticOutputParser(pydantic_object=FlashcardDeck)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor creating a flashcard deck for exam revision.\n\n"
         "Generate exactly {num_cards} flashcards on the topic: {topic}\n\n"
         "RULES:\n"
         "- Use ONLY the course material provided below. Do not use outside knowledge.\n"
         "- front: one concept, term, formula, or question — short enough to fit a card.\n"
         "- back: the definition, explanation, or answer — concise but complete.\n"
         "- Cover a range of concepts spread across the material, not just the first few.\n"
         "- No duplicates. Each card must test something distinct.\n"
         "- Prioritize high-yield exam concepts: definitions, formulas, key distinctions, "
         "common pitfalls.\n\n"
         "Course material:\n{context}\n\n"
         "{format_instructions}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    chain = prompt | model | parser
    return chain.invoke({
        "topic": topic,
        "num_cards": num_cards,
        "context": context,
        "format_instructions": format_instructions,
    })


def generate_practice_paper(course_id: str, course_name: str, instructions: str) -> PracticePaper:
    # k=12 for broad topic coverage across the full course, not just one concept
    context = retrieve_context("exam topics key concepts overview", course_id, k=12)
    if not context:
        raise ValueError("No course material found. Upload documents first.")

    parser = PydanticOutputParser(pydantic_object=PracticePaper)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor setting a university exam paper for the course: {course_name}.\n\n"
         "INSTRUCTOR INSTRUCTIONS:\n{instructions}\n\n"
         "PAPER REQUIREMENTS:\n"
         "- Create exactly 3 sections: Section A (MCQ, 1-2 marks each), "
         "Section B (Short Answer, 3-5 marks each), Section C (Long Answer, 10-15 marks each)\n"
         "- Section A: 5 MCQ questions (include the options in the question text itself)\n"
         "- Section B: 3 short answer questions\n"
         "- Section C: 2 long answer questions\n"
         "- Each section must have a brief instruction line (e.g. 'Attempt all questions. 1 mark each.')\n"
         "- Every question MUST have a complete model answer — not a hint, the full answer\n"
         "- Questions must be exam-quality and grounded in the course material below\n"
         "- Do not repeat concepts across questions\n\n"
         "COURSE MATERIAL:\n{context}\n\n"
         "{format_instructions}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    chain = prompt | model | parser
    return chain.invoke({
        "course_name": course_name,
        "instructions": instructions or "Standard university exam paper. Cover all major topics.",
        "context": context,
        "format_instructions": format_instructions,
    })
