import re
import chromadb
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from core.llm import get_model, UsageTracker


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


# ─── LATEX MODELS ─────────────────────────────────────────────────────────────

class CodeBlock(BaseModel):
    caption: str = ""
    language: str = "text"
    code: str

class MCQFact(BaseModel):
    label: str   # "Stable", "Adaptive", "Best Case", "Extra Space"
    value: str   # "Yes", "$O(n)$", "$O(1)$"

class WorkedExample(BaseModel):
    title: str
    problem_statement: str = ""
    answer_idea: str = ""
    code: Optional[CodeBlock] = None   # code shown here, coupled with its trace
    trace: str = ""                    # step-by-step trace showing structure state after each op

class ExamTrace(BaseModel):
    question: str       # exact exam-style question e.g. "State array after Pass 2. Input: [6,3,1,5]"
    steps: list[str]    # ["Pass 1: [3,1,5,6]", "Pass 2: [1,3,5,6]"]
    answer: str         # "[1,3,5,6]"

class PatternHint(BaseModel):
    keywords: str   # exam trigger phrases: "reverse list / flip links / reverse pointers"
    think: str      # what to immediately apply: "prev / cur / next three-pointer"

class ComparisonRow(BaseModel):
    feature: str
    left: str
    right: str

class ComparisonTable(BaseModel):
    title: str        # "Stack vs Queue"
    left_label: str   # "Stack"
    right_label: str  # "Queue"
    rows: list[ComparisonRow]

class LatexSubsection(BaseModel):
    title: str
    body: str = ""                         # core idea: 2-5 sentences, complexity in last sentence
    mcq_facts: list[MCQFact] = []          # quick-reference properties (Stable/Adaptive/Best/Worst/Space)
    bullets: list[str] = []                # key technical rules
    patterns: list[PatternHint] = []       # keyword triggers → algorithm to apply
    worked_examples: list[WorkedExample] = []
    exam_traces: list[ExamTrace] = []      # exam-style trace questions
    exam_moves: list[str] = []
    pitfalls: list[str] = []
    ascii_diagrams: list[str] = []         # ASCII art: "[5] -> [10] -> [15] -> NULL"
    common_exam_questions: list[str] = []  # most-asked question types for this concept

class LatexSection(BaseModel):
    title: str
    subsections: list[LatexSubsection]
    comparison_table: Optional[ComparisonTable] = None  # e.g. Stack vs Queue, SLL vs DLL
    master_example: str = ""               # one canonical structure used across all ops in section

class ComplexityRow(BaseModel):
    operation: str
    complexity: str
    note: str = ""

class LatexNotesDocument(BaseModel):
    course_code: str
    course_name: str
    topic: str
    sections: list[LatexSection]
    complexity_table: list[ComplexityRow] = []
    final_checklist: list[str] = []


# ─── HELPER ───────────────────────────────────────────────────────────────────

def retrieve_context(topic: str, course_id: str, k: int = 6) -> str:
    vectorstore_path = Path("vectorstore") / course_id
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
        "Structure each section as markdown in this exact order:\n\n"
        "**Definition** — 2-3 sentences. Last sentence always states complexity.\n\n"
        "**Pattern Recognition** — keyword triggers mapped to techniques:\n"
        "  Format each as: 'See [trigger phrase] → apply [specific technique]'\n"
        "  Examples: 'reverse list / flip links → prev/cur/next three-pointer'\n"
        "             'kth from end → fast-slow gap: advance fast k steps, then move both'\n"
        "             'cycle / loop detection → Floyd tortoise-hare: slow+1, fast+2'\n"
        "  Be SPECIFIC — never write 'use a loop' or 'use recursion'.\n\n"
        "**Worked Examples** — cover EVERY question variant for this concept:\n"
        "  - Normal case (typical input)\n"
        "  - Empty or single-element input\n"
        "  - Already sorted / reverse sorted (where relevant)\n"
        "  - Duplicate elements\n"
        "  - Boundary operations: head insert/delete, tail insert/delete, middle\n"
        "  Each example MUST have: complete working code (not pseudocode) PLUS\n"
        "  a full step-by-step trace showing exact data structure state after EVERY\n"
        "  single operation — no '...continues...' or 'similar to above'.\n"
        "  End each example with Time complexity and Space complexity.\n\n"
        "**Exam Moves** — 2-3 techniques that directly score marks.\n\n"
        "**Pitfalls** — 1-2 mistakes students make with their consequence.\n\n"
        "ANTI-PATTERNS — never do these:\n"
        "- Never write code without a matching step-by-step trace\n"
        "- Never use '...continues...' — every step must be explicit\n"
        "- Never skip edge cases (empty, single, duplicates, boundary)\n"
        "- Never write vague pattern hints like 'use two pointers'\n"
        "Complexity notation: $O(n)$, $O(n^2)$, $O(\\log n)$\n"
        "Use only the course material below."
    ),
    "revision": (
        "You are writing REVISION NOTES. Use ONLY bullet points — zero prose paragraphs.\n"
        "Each section must be scannable in under 30 seconds.\n"
        "Format per concept in this exact structure:\n"
        "- **Definition:** [one line]\n"
        "- **Complexity:** Best $O(?)$ / Avg $O(?)$ / Worst $O(?)$ / Space $O(?)$\n"
        "  — Complexity is MANDATORY for every concept. Never omit it.\n"
        "- **Key property:** [one line — e.g. 'Stable: Yes', 'In-place: Yes']\n"
        "- **Pattern:** See [trigger phrase] → [specific technique, not vague]\n"
        "- **Trace:** [3-4 step trace of most common operation, no full code]\n"
        "- **Exam move:** [one actionable tip]\n"
        "- **Pitfall:** [one common mistake]\n\n"
        "RULES:\n"
        "- Complexity MUST use $O()$ notation: $O(n)$, $O(n^2)$, $O(\\log n)$\n"
        "- Pattern hints MUST be specific: 'three-pointer (prev/cur/next)' not 'use pointers'\n"
        "- No full sentences, no theory paragraphs — bullets only\n"
        "Use only the course material below."
    ),
    "exam": (
        "You are writing EXAM CHEAT NOTES. Absolutely NO prose.\n"
        "Each section contains ONLY these items:\n"
        "- **Complexity:** Best $O(?)$ / Avg $O(?)$ / Worst $O(?)$ / Space $O(?)$\n"
        "- **Pattern:** See [trigger] → [specific technique]\n"
        "  Examples: 'balance check → use a stack, push open brackets, pop on close'\n"
        "            'kth from end → fast pointer advances k steps first'\n"
        "            'stable sort needed → Merge, Insertion, Bubble only'\n"
        "- **Exam move:** [technique that directly scores marks]\n"
        "- **Pitfall:** [trap + consequence]\n"
        "- **Quick Trace:** the most common exam trace question, 2-3 steps only\n\n"
        "End with a FAST REVISION CHECKLIST — 12-15 items, format: 'Term → answer':\n"
        "  'Bubble Sort → Stable, $O(n^2)$, adaptive with flag'\n"
        "  'Merge Sort space → $O(n)$ extra'\n"
        "  'Binary search prerequisite → sorted array'\n"
        "  'Stack order → LIFO', 'Queue order → FIFO'\n\n"
        "RULES:\n"
        "- Pattern hints MUST be specific — never 'use a loop' or 'use recursion'\n"
        "- Complexity notation: $O(n)$, $O(n^2)$, $O(\\log n)$\n"
        "- No section without a Complexity line\n"
        "Use only the course material below."
    ),
    "cheat_sheet": (
        "You are writing a ONE-PAGE CHEAT SHEET. Ultra-compact — every word must earn its place.\n"
        "Every section contains ONLY these line types:\n"
        "- Complexity: 'B/A/W/S: $O(?)$ / $O(?)$ / $O(?)$ / $O(?)$'\n"
        "- Pattern: '[trigger] → [technique]'\n"
        "- Fact: max 5 words\n\n"
        "3-6 lines per section. No examples, no explanations, no full sentences.\n"
        "Pattern lines must be SPECIFIC: 'reverse → prev/cur/next' not 'use pointers'.\n"
        "Use only the course material below."
    ),
}


def generate_notes(topic: str, note_type: str, course_id: str, provider: str = "cerebras") -> NoteDocument:
    context = _retrieve_multi_topic(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")
    system = _NOTE_SYSTEM_PROMPTS.get(note_type, _NOTE_SYSTEM_PROMPTS["detailed"])
    prompt = ChatPromptTemplate.from_messages([
        ("system", system + "\n\nTopic: {topic}\n\nCourse material:\n{context}"),
    ])
    tracker = UsageTracker()
    chain = prompt | get_model(provider).with_structured_output(NoteDocument)
    return chain.invoke({"topic": topic, "context": context}, config={"callbacks": [tracker]})


def generate_quiz(topic: str, course_id: str, num_questions: int = 5, provider: str = "cerebras") -> QuizDocument:
    context = _retrieve_multi_topic(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor writing an exam-style MCQ quiz.\n\n"
         "Generate exactly {num_questions} MCQ questions on the topic: {topic}\n\n"
         "QUESTION TYPE MIX — distribute questions across these types:\n"
         "  (a) Recall — definition or property ('Which sort is stable?')\n"
         "  (b) Trace — state after an operation ('Array after pass 2 of Bubble Sort on [5,3,1,4]?')\n"
         "  (c) Complexity — time/space complexity of an operation\n"
         "  (d) Comparison — distinguish two concepts ('SLL vs DLL: which needs prev pointer?')\n"
         "  (e) Application — which technique to apply ('To find a cycle, use...')\n"
         "For {num_questions} questions aim for roughly equal distribution across (a)-(e).\n\n"
         "DISTRACTOR QUALITY:\n"
         "  - Wrong options must be common student misconceptions or off-by-one errors\n"
         "  - Never make wrong options obviously wrong — they should fool a student who half-knows\n"
         "  - For trace questions: wrong options = common mistakes at each step\n\n"
         "RULES:\n"
         "- Use ONLY the course material provided below. Do not use outside knowledge.\n"
         "- Each question must have exactly 4 options written as full sentences, not letters.\n"
         "- The 'correct' field must be copied EXACTLY from one of the options — "
         "not 'A', not 'option 1', the full string verbatim.\n"
         "- Explanation: state WHY the correct answer is right AND why each wrong option is wrong.\n"
         "- No trivial questions where the answer is obvious from the question text.\n"
         "- Cover different concepts — never two questions testing the same fact.\n\n"
         "ANTI-PATTERNS:\n"
         "- Never ask 'What does X stand for?' — too trivial\n"
         "- Never include an option that is clearly impossible\n"
         "- Never repeat the same complexity tested twice\n\n"
         "Course material:\n{context}"),
    ])
    chain = prompt | get_model(provider).with_structured_output(QuizDocument)
    return chain.invoke({"topic": topic, "num_questions": num_questions, "context": context})


def generate_flashcards(topic: str, course_id: str, num_cards: int = 10, provider: str = "cerebras") -> FlashcardDeck:
    context = _retrieve_multi_topic(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor creating a flashcard deck for exam revision.\n\n"
         "Generate exactly {num_cards} flashcards on the topic: {topic}\n\n"
         "CARD TYPE MIX — spread cards across these categories:\n"
         "  Definition: front='What is X?' back='[one-sentence definition]'\n"
         "  Complexity: front='Time/Space complexity of X?' back='Best O(?) / Avg O(?) / Worst O(?) / Space O(?)'\n"
         "  Pattern: front='Exam says: [trigger phrase]' back='Apply: [specific technique]'\n"
         "    Example: front='Exam says: find kth node from end'\n"
         "             back='Fast-slow gap: advance fast k steps, then move both until fast=NULL'\n"
         "  Comparison: front='X vs Y — key difference?' back='[1-2 line contrast with examples]'\n"
         "  Pitfall: front='Common mistake with X?' back='[mistake + why it fails + correct approach]'\n"
         "  Trace: front='Trace [operation] on [small input]' back='[step-by-step state changes]'\n\n"
         "For {num_cards} cards target this rough split:\n"
         "  ~25% Complexity, ~20% Pattern, ~20% Definition, ~15% Comparison, ~10% Pitfall, ~10% Trace\n\n"
         "RULES:\n"
         "- Use ONLY the course material provided below. Do not use outside knowledge.\n"
         "- front: short enough to read in 3 seconds.\n"
         "- back: concise but complete — a student should be able to write this in an exam.\n"
         "- No duplicates. Each card tests something distinct.\n"
         "- Complexity cards MUST use $O()$ notation: $O(n)$, $O(n^2)$, $O(\\log n)$\n"
         "- Pattern cards MUST be specific: 'three-pointer (prev/cur/next)' not 'use pointers'\n\n"
         "ANTI-PATTERNS:\n"
         "- Never two cards testing the same complexity\n"
         "- Never a front that gives away the answer ('What is the LIFO data structure?' → Stack)\n"
         "- Never vague backs like 'it depends' or 'varies'\n\n"
         "Course material:\n{context}"),
    ])
    chain = prompt | get_model(provider).with_structured_output(FlashcardDeck)
    return chain.invoke({"topic": topic, "num_cards": num_cards, "context": context})


def generate_practice_paper(course_id: str, course_name: str, instructions: str, provider: str = "cerebras") -> PracticePaper:
    # k=12 for broad topic coverage across the full course, not just one concept
    context = retrieve_context("exam topics key concepts overview", course_id, k=12)
    if not context:
        raise ValueError("No course material found. Upload documents first.")
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor setting a university exam paper for the course: {course_name}.\n\n"
         "INSTRUCTOR INSTRUCTIONS:\n{instructions}\n\n"
         "PAPER STRUCTURE:\n"
         "- Section A: MCQ, 5 questions, 1-2 marks each. Include 4 options in the question text.\n"
         "- Section B: Short Answer, 3 questions, 3-5 marks each.\n"
         "- Section C: Long Answer, 2 questions, 10-15 marks each.\n"
         "Each section needs a one-line instruction (e.g. 'Attempt all. 2 marks each.').\n\n"
         "QUESTION TYPE REQUIREMENTS:\n"
         "Section A — MCQ type mix:\n"
         "  At least 1 trace question ('Array after pass N?'), 1 complexity question,\n"
         "  1 comparison ('Which is stable?'), 1 application ('To detect a cycle, use...')\n"
         "Section B — Short answer type mix:\n"
         "  At least 1 trace/state question, 1 code-writing question (with specific input),\n"
         "  1 analysis question (prove complexity, explain behaviour on edge input)\n"
         "Section C — Long answer type mix:\n"
         "  At least 1 full algorithm trace (normal input + 1 edge case),\n"
         "  1 design/implementation question (write complete code + dry run it)\n\n"
         "MODEL ANSWER QUALITY — this is the most important rule:\n"
         "- Every model answer must be complete enough to award full marks — not a hint.\n"
         "- Trace questions: show exact data structure state after EVERY single step.\n"
         "  Example for bubble sort: 'Pass 1: [5,3,1,4] → swap 5,3 → [3,5,1,4] →\n"
         "  swap 5,1 → [3,1,5,4] → swap 5,4 → [3,1,4,5]'\n"
         "- Code questions: provide complete working code, not pseudocode.\n"
         "- Analysis questions: show the derivation, not just the answer.\n"
         "- Long answer model answers must cover: normal case trace + edge case + complexity\n\n"
         "ANTI-PATTERNS:\n"
         "- Never repeat the same concept across sections\n"
         "- Never write model answers like 'Use Dijkstra's algorithm' — show the actual steps\n"
         "- Never include obviously wrong MCQ options\n"
         "- Never skip edge cases in Section C model answers\n\n"
         "COURSE MATERIAL:\n{context}"),
    ])
    chain = prompt | get_model(provider).with_structured_output(PracticePaper)
    return chain.invoke({
        "course_name": course_name,
        "instructions": instructions or "Standard university exam paper. Cover all major topics.",
        "context": context,
    })


_TOPIC_EXPANSIONS: dict[str, list[str]] = {
    # Sorting
    "sorting": ["Bubble Sort", "Selection Sort", "Insertion Sort", "Quick Sort", "Merge Sort"],
    "sorting algorithms": ["Bubble Sort", "Selection Sort", "Insertion Sort", "Quick Sort", "Merge Sort"],
    "sorts": ["Bubble Sort", "Selection Sort", "Insertion Sort", "Quick Sort", "Merge Sort"],
    # Searching
    "searching": ["Linear Search", "Binary Search"],
    "search": ["Linear Search", "Binary Search"],
    "search algorithms": ["Linear Search", "Binary Search"],
    # Trees
    "trees": ["Binary Search Tree", "BST Insert/Delete/Search", "Tree Traversals", "AVL Trees"],
    "tree": ["Binary Search Tree", "BST Insert/Delete/Search", "Tree Traversals"],
    "bst": ["BST Operations", "BST Traversals", "BST Height and LCA"],
    # Hashing
    "hashing": ["Hash Functions", "Hash Tables and Chaining", "Open Addressing and Load Factor"],
    # Arrays — include insert/delete at index and rotations
    "arrays": [
        "Array Traversal and Access",
        "Array Insert at Index and Delete at Index",
        "Array Left Rotation and Right Rotation",
    ],
    "array": [
        "Array Traversal and Access",
        "Array Insert at Index and Delete at Index",
        "Array Left Rotation and Right Rotation",
    ],
    # Linked Lists — SLL and DLL each get a full dedicated chapter with ALL operations
    "linked list": [
        "Singly Linked List: push_front, push_back, insert_at_position, delete_node, search, reverse",
        "Doubly Linked List: push_front, push_back, pop_front, pop_back, insert_before, insert_after, delete_node, reverse - cover prev pointer updates",
    ],
    "linked lists": [
        "Singly Linked List: push_front, push_back, insert_at_position, delete_node, search, reverse",
        "Doubly Linked List: push_front, push_back, pop_front, pop_back, insert_before, insert_after, delete_node, reverse - cover prev pointer updates",
    ],
    # Recursion
    "recursion": ["Recursion Fundamentals", "Fibonacci (naive vs memoised)", "Tower of Hanoi"],
    # Graphs
    "graphs": ["Graph Representation", "BFS", "DFS"],
    "graph": ["Graph Representation", "BFS", "DFS"],
    # Stacks — operations + classic applications
    "stack": [
        "Stack Operations and Implementation (array-based and linked-list-based)",
        "Stack Applications: Balanced Parentheses, Infix to Postfix Conversion, Postfix Evaluation",
    ],
    "stacks": [
        "Stack Operations and Implementation (array-based and linked-list-based)",
        "Stack Applications: Balanced Parentheses, Infix to Postfix Conversion, Postfix Evaluation",
    ],
    # Queues — operations + circular queue
    "queue": [
        "Queue Operations and Implementation (array-based and linked-list-based)",
        "Circular Queue: implementation, wrap-around logic, full vs empty detection",
    ],
    "queues": [
        "Queue Operations and Implementation (array-based and linked-list-based)",
        "Circular Queue: implementation, wrap-around logic, full vs empty detection",
    ],
    # Combined — stacks + queues together
    "stacks and queues": [
        "Stack Operations and Implementation (array-based and linked-list-based)",
        "Stack Applications: Balanced Parentheses, Infix to Postfix Conversion, Postfix Evaluation",
        "Queue Operations and Implementation (array-based and linked-list-based)",
        "Circular Queue: implementation, wrap-around logic, full vs empty detection",
    ],
    "stack and queue": [
        "Stack Operations and Implementation (array-based and linked-list-based)",
        "Stack Applications: Balanced Parentheses, Infix to Postfix Conversion, Postfix Evaluation",
        "Queue Operations and Implementation (array-based and linked-list-based)",
        "Circular Queue: implementation, wrap-around logic, full vs empty detection",
    ],
    # Deque
    "deque": [
        "Deque (Double-Ended Queue): push_front, push_back, pop_front, pop_back, peek_front, peek_back",
    ],
    "deques": [
        "Deque (Double-Ended Queue): push_front, push_back, pop_front, pop_back, peek_front, peek_back",
    ],
}


def _retrieve_multi_topic(topic: str, course_id: str) -> str:
    """Retrieve context for multi-topic queries by querying each sub-topic separately."""
    import re as _re
    sub_topics = [t.strip() for t in _re.split(r'[,/]|\band\b', topic, flags=_re.IGNORECASE) if t.strip()]
    if len(sub_topics) <= 1:
        return retrieve_context(topic, course_id, k=12)
    per_k = max(4, 20 // len(sub_topics))
    seen, parts = set(), []
    for st in sub_topics:
        ctx = retrieve_context(st, course_id, k=per_k)
        if ctx and ctx not in seen:
            seen.add(ctx)
            parts.append(f"[--- {st.upper()} ---]\n{ctx}")
    return "\n\n".join(parts) if parts else retrieve_context(topic, course_id, k=12)


def _generate_latex_notes_single(
    topic: str, course_id: str, course_name: str = "", provider: str = "cerebras"
) -> LatexNotesDocument:
    context = _retrieve_multi_topic(topic, course_id)
    if not context:
        raise ValueError("No course material found for this topic.")
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a professor creating open-book exam notes with maximum teaching density.\n"
         "The single most important rule: EXAMPLES AND TRACES first, then code. Every concept\n"
         "must be understood through worked examples before the student sees the full code.\n\n"
         "STRUCTURE — follow this order inside EVERY subsection:\n\n"
         "1. body: Core idea in 2-5 plain sentences. Last sentence states complexity.\n"
         "   Example: 'Bubble Sort swaps adjacent out-of-order elements repeatedly. The largest\n"
         "   element settles at the end after each pass. With a swapped flag it is adaptive:\n"
         "   best $O(n)$, worst $O(n^2)$.'\n\n"
         "2. mcq_facts: Quick-reference properties a student needs for MCQ/short-answer.\n"
         "   Always include: Stable, Adaptive, In-place (or equivalent for the concept),\n"
         "   Best Case, Worst Case, Extra Space.\n"
         "   Example: [{{label:'Stable',value:'Yes'}},{{label:'Best',value:'$O(n)$'}},...]\n\n"
         "3. bullets: 3-5 key technical rules as short plain-text strings.\n\n"
         "3b. patterns: 2-4 pattern recognition hints. When an exam question contains\n"
         "   certain keywords, the student must immediately know what technique to apply.\n"
         "   keywords: slash-separated trigger phrases seen in exam Qs\n"
         "   think:    the SPECIFIC technique — never vague like 'use a loop'\n"
         "   Concrete examples (copy this level of specificity):\n"
         "     keywords='reverse list / flip links / reverse pointers'\n"
         "       think='prev / cur / next three-pointer — reassign cur.next=prev'\n"
         "     keywords='kth from end / nth from last / distance from tail'\n"
         "       think='fast-slow gap: advance fast k steps, then move both'\n"
         "     keywords='cycle / loop detection / infinite loop'\n"
         "       think='Floyd tortoise-hare: slow+1, fast+2; meet inside cycle'\n"
         "     keywords='find middle / split list / median node'\n"
         "       think='slow+1 fast+2; when fast=NULL slow is at middle'\n"
         "     keywords='merge two sorted / combine ordered lists'\n"
         "       think='dummy head + compare front nodes, advance smaller pointer'\n"
         "     keywords='not stable / stability question'\n"
         "       think='stable sorts: Bubble, Insertion, Merge; unstable: Selection, Quick, Heap'\n\n"
         "4. worked_examples: Cover every DISTINCT question type an examiner could ask.\n"
         "   Variants to include (where applicable to the concept):\n"
         "   - Normal case (typical non-trivial input)\n"
         "   - Empty / single-element input\n"
         "   - Already sorted / reverse sorted (for sorting)\n"
         "   - Duplicate elements\n"
         "   - Target not found (for search)\n"
         "   - Boundary insertions/deletions (head, tail, middle)\n"
         "   If two variants test the same underlying mechanic, write ONE example, not two.\n"
         "   Each example MUST pair CODE with a full step-by-step TRACE showing the exact\n"
         "   data structure state after EVERY single operation — no vague '...continues...'.\n"
         "   Example trace for Bubble Sort:\n"
         "   'Input [5,1,4,2]: compare 5,1 → swap → [1,5,4,2]; compare 5,4 → swap →\n"
         "    [1,4,5,2]; compare 5,2 → swap → [1,4,2,5]. Pass 1 done.'\n\n"
         "5. exam_traces: 3-4 exam-style trace questions — the exact type examiners ask.\n"
         "   Always include: (a) normal input, (b) edge case (empty/single/already-sorted),\n"
         "   (c) duplicate elements, (d) boundary operation (head/tail insert or delete).\n"
         "   question: 'State the array after the second pass. Input: [6,3,1,5]'\n"
         "   steps: ['Pass 1: [3,1,5,6]  (6 bubbled right)', 'Pass 2: [1,3,5,6]  (5 settled)']\n"
         "   answer: '[1,3,5,6]'\n\n"
         "6. exam_moves: 1-3 tips that directly score marks in an exam.\n\n"
         "7. pitfalls: 1-2 common student mistakes with brief consequence.\n\n"
         "8. ascii_diagrams: 1-3 ASCII art diagrams showing data structure state.\n"
         "   Use ONLY printable ASCII — arrows as '->', pointer as '-> NULL', boxes as [val].\n"
         "   Examples:\n"
         "     '[10] -> [20] -> [30] -> NULL'\n"
         "     'head -> [10] -> [20] -> [30] -> NULL <- tail'\n"
         "     '      50     '\n"
         "     '     /  \\   '\n"
         "     '   30    70  '\n"
         "     '   / \\      '\n"
         "     ' 20  40      '\n"
         "   Max 5 lines, max 60 chars wide. Show BEFORE and AFTER for operations.\n\n"
         "9. common_exam_questions: 3-5 highest-frequency question types examiners ask.\n"
         "   These are question TEMPLATES, not answers. Be specific, not generic.\n"
         "   Examples:\n"
         "     'Trace deletion of node 30 from list 10->20->30->40->NULL'\n"
         "     'State the array contents after Pass 2 of Bubble Sort on [5,3,8,1,2]'\n"
         "     'Is Selection Sort stable? Explain with a counter-example.'\n"
         "     'What is the worst-case time complexity of Quick Sort and when does it occur?'\n"
         "     'Perform an inorder traversal on the given BST and state the output'\n\n"
         "ANTI-PATTERNS — never do these:\n"
         "- Do NOT write code without a trace, or a trace without code.\n"
         "- Do NOT write vague traces ('...continues...', 'similar to above'). Every step explicit.\n"
         "- Do NOT repeat two examples that test the same underlying mechanic — merge them.\n"
         "- Do NOT skip edge cases (empty, single element, duplicates, boundary operations).\n"
         "- Do NOT create a new section for every individual operation — group related operations\n"
         "  (insertions together, deletions together, traversal/search together).\n\n"
         "OTHER RULES:\n"
         "- Group logically: related operations belong in the same section. Use as many sections\n"
         "  as the topic genuinely needs — not one per operation, not one for everything.\n"
         "- master_example (section-level): ONE canonical data structure used across ALL\n"
         "  operations in this section so the student can compare operations side by side.\n"
         "  Linked Lists: '10 -> 20 -> 30 -> 40 -> 50 -> NULL'\n"
         "  Sorting: '[64, 25, 12, 22, 11]'\n"
         "  BST: 'root=50, left=30, right=70, 30.left=20, 30.right=40'\n"
         "  If the section genuinely has no single structure, set to ''.\n"
         "- comparison_table (section-level): REQUIRED when the section covers two comparable\n"
         "  concepts. If only one concept is covered with no natural comparison, set rows=[].\n"
         "  Never omit this field — always include it, even if rows=[]. Good triggers:\n"
         "  SLL vs DLL, Array Stack vs Linked Stack, Stack vs Queue, Bubble vs Selection,\n"
         "  Stable vs Unstable sorts, Linear vs Binary search, Array vs Linked List.\n"
         "  Rows must cover at least: Order/Type, Memory layout, Best/Worst complexity,\n"
         "  Key operation, Use-when. Example for Stack vs Queue:\n"
         "    title='Stack vs Queue', left_label='Stack', right_label='Queue'\n"
         "    rows: [{{feature:'Order',left:'LIFO',right:'FIFO'}},\n"
         "           {{feature:'Insert',left:'push() at top',right:'enqueue() at rear'}},\n"
         "           {{feature:'Delete',left:'pop() from top',right:'dequeue() from front'}},\n"
         "           {{feature:'Peek',left:'top element',right:'front element'}},\n"
         "           {{feature:'Use when',left:'undo/backtrack/DFS',right:'scheduling/BFS'}}]\n"
         "- complexity_table: every operation mentioned, with complexity and a one-line reason\n"
         "- final_checklist: 12-14 one-line MCQ/short-answer facts. Format: 'Term → answer'.\n"
         "  Examples: 'Bubble Sort stability → Stable', 'Merge Sort space → O(n) extra',\n"
         "  'Binary search prerequisite → sorted array', 'Stack order → LIFO'.\n"
         "  These are exam quick-reference facts, NOT 'Can you...' questions.\n"
         "- Complexity notation: $O(n)$, $O(n^2)$, $O(\\log n)$ (LaTeX inline math)\n"
         "- Plain text in body/bullets/exam_moves/pitfalls — no markdown bold or backticks\n"
         "- Use ONLY the course material below\n\n"
         "Topic: {topic}\n\nCourse material:\n{context}"),
    ])
    tracker = UsageTracker()
    chain = prompt | get_model(provider).with_structured_output(LatexNotesDocument)
    return chain.invoke({"topic": topic, "context": context}, config={"callbacks": [tracker]})


def generate_latex_notes(
    topic: str, course_id: str, course_name: str = "", provider: str = "cerebras",
    progress_callback=None,
) -> LatexNotesDocument:
    """Generate LaTeX notes. For comma-separated topics, generates each separately then merges.

    progress_callback(i, n, topic_name) is called after each topic completes.
    _retrieve_multi_topic handles slash-separated sub-topics within a single topic entry
    (e.g. 'Arrays/Vectors'); the comma splitting here handles separate major topics.
    """
    clean = re.sub(r'^[Ss]yllabus\s*:\s*', '', topic).strip()
    comma_topics = [t.strip() for t in clean.split(',') if t.strip()]

    # Expand known compound topics (e.g. "Sorting" → 5 individual algorithms)
    major_topics: list[str] = []
    for t in comma_topics:
        expansion = _TOPIC_EXPANSIONS.get(t.lower())
        if expansion:
            major_topics.extend(expansion)
        else:
            major_topics.append(t)

    if len(major_topics) <= 1:
        return _generate_latex_notes_single(major_topics[0] if major_topics else clean, course_id, course_name, provider)

    docs = []
    for i, t in enumerate(major_topics, 1):
        doc = _generate_latex_notes_single(t, course_id, course_name, provider)
        docs.append(doc)
        if progress_callback:
            progress_callback(i, len(major_topics), t)

    merged = docs[0]
    merged.topic = clean
    for d in docs[1:]:
        merged.sections.extend(d.sections)
        merged.complexity_table.extend(d.complexity_table)
        seen = set(merged.final_checklist)
        for item in d.final_checklist:
            if item not in seen:
                merged.final_checklist.append(item)
                seen.add(item)
    return merged
