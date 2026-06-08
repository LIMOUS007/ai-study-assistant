import os
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
# from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
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
    # embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
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

_NOTE_SYSTEM_PROMPTS = {
    "detailed": (
        "You are a professor writing comprehensive open-book exam notes.\n"
        "Write in full prose paragraphs like a textbook. Each concept gets:\n"
        "- A full definition paragraph\n"
        "- A 'Exam move:' callout\n"
        "- A 'Pitfall:' callout\n"
        "- A fully-traced worked example with real input, step-by-step execution, "
        "complete code (not pseudocode), and Time/Space complexity\n"
        "End with a summary section covering key patterns and common exam questions.\n"
        "Be long, thorough, and detailed. Use only the course material below."
    ),
    "revision": (
        "You are writing REVISION NOTES. Use ONLY bullet points — zero prose paragraphs.\n"
        "Each section must be scannable in under 30 seconds.\n"
        "Format per concept:\n"
        "• Definition: [one line]\n"
        "• Key property: [one line]\n"
        "• Complexity: [O(?) best/avg/worst]\n"
        "• Example: [one 2-line trace, no full code]\n"
        "No callout labels, no full sentences, no theory. Bullet points only.\n"
        "Use only the course material below."
    ),
    "exam": (
        "You are writing EXAM CHEAT NOTES. Absolutely NO prose.\n"
        "Each section contains ONLY:\n"
        "- Complexity table (Best | Avg | Worst | Space)\n"
        "- 'Exam move:' bullets — techniques that score marks\n"
        "- 'Pitfall:' bullets — traps students fall into\n"
        "- 'Common mistake:' bullets — frequent errors\n"
        "End with a fast-revision checklist (tick-box style).\n"
        "If a section has no callouts, do not include it.\n"
        "Use only the course material below."
    ),
    "cheat_sheet": (
        "You are writing a ONE-PAGE CHEAT SHEET. Ultra-compact.\n"
        "Rules:\n"
        "- Max 5 words per bullet point\n"
        "- Complexities and formulas ONLY\n"
        "- No examples, no explanations, no full sentences\n"
        "- No callout labels\n"
        "Every section is a list of 3-6 ultra-short bullets. Nothing else.\n"
        "Use only the course material below."
    ),
}


def generate_notes(topic: str, note_type: str, course_id: str) -> NoteDocument:
    context = retrieve_context(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")

    system = _NOTE_SYSTEM_PROMPTS.get(note_type, _NOTE_SYSTEM_PROMPTS["detailed"])
    prompt = ChatPromptTemplate.from_messages([
        ("system", system + "\n\nTopic: {topic}\n\nCourse material:\n{context}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("groq_api_key"), http_client=httpx.Client(verify=False))
    model = ChatOpenAI(model="gpt-oss-120b", base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY"), http_client=httpx.Client(verify=False))
    chain = prompt | model.with_structured_output(NoteDocument)
    return chain.invoke({"topic": topic, "context": context})


def generate_quiz(topic: str, quiz_type: str, course_id: str, num_questions: int = 5) -> QuizDocument:
    context = retrieve_context(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")

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
         "Course material:\n{context}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("groq_api_key"), http_client=httpx.Client(verify=False))
    model = ChatOpenAI(model="gpt-oss-120b", base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY"), http_client=httpx.Client(verify=False))
    chain = prompt | model.with_structured_output(QuizDocument)
    return chain.invoke({
        "topic": topic,
        "num_questions": num_questions,
        "context": context,
    })


def generate_flashcards(topic: str, course_id: str, num_cards: int = 10) -> FlashcardDeck:
    context = retrieve_context(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")

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
         "Course material:\n{context}"),
    ])

    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("groq_api_key"), http_client=httpx.Client(verify=False))
    model = ChatOpenAI(model="gpt-oss-120b", base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY"), http_client=httpx.Client(verify=False))
    chain = prompt | model.with_structured_output(FlashcardDeck)
    return chain.invoke({
        "topic": topic,
        "num_cards": num_cards,
        "context": context,
    })


def generate_practice_paper(course_id: str, course_name: str, instructions: str) -> PracticePaper:
    # k=12 for broad topic coverage across the full course, not just one concept
    context = retrieve_context("exam topics key concepts overview", course_id, k=12)
    if not context:
        raise ValueError("No course material found. Upload documents first.")

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

    parser = JsonOutputParser(pydantic_object=PracticePaper)
    # model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("groq_api_key"), http_client=httpx.Client(verify=False))
    model = ChatOpenAI(model="gpt-oss-120b", base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY"), http_client=httpx.Client(verify=False))
    model_json = model.bind(response_format={"type": "json_object"})
    chain = prompt | model_json | parser
    return chain.invoke({
        "course_name": course_name,
        "instructions": instructions or "Standard university exam paper. Cover all major topics.",
        "context": context,
        "format_instructions": parser.get_format_instructions(),
    })
