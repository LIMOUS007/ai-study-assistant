from pydantic import BaseModel
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser


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


def academic_response_to_markdown(response: AcademicResponse) -> str:
    parts = [
        f"#### {response.question_repeated}",
        f"#### Professor's Explanation\n\n{response.professor_explanation}",
        f"#### In Simple Terms\n\n{response.beginner_explanation}",
    ]
    if response.analogy:
        parts.append(f"#### Analogy\n\n{response.analogy}")
    parts += [
        f"#### Theory & Concepts\n\n{response.theory_and_concepts}",
        f"#### Worked Examples\n\n{response.worked_examples}",
    ]
    if response.common_mistakes:
        parts.append(f"#### Common Mistakes\n\n{response.common_mistakes}")
    if response.practice_questions:
        qa_blocks = [
            f"**{i}.** {qa.question}\n\n{qa.answer}"
            for i, qa in enumerate(response.practice_questions, 1)
        ]
        parts.append(f"#### Practice Questions\n\n" + "\n\n".join(qa_blocks))
    return "\n\n".join(parts)


def get_academic_parser() -> PydanticOutputParser:
    return PydanticOutputParser(pydantic_object=AcademicResponse)


def build_academic_prompt(system_prompt: str) -> ChatPromptTemplate:
    parser = get_academic_parser()
    format_instructions = parser.get_format_instructions()
    system_message = (
        "{system_prompt}\n\n"
        "You are an academic professor. Use the structured format below ONLY when the student asks "
        "a subject-matter or conceptual question (explaining a topic, asking how something works, "
        "requesting examples, etc.). For conversational messages, code reviews, simple yes/no questions, "
        "or follow-ups that don't require teaching, respond naturally in the appropriate fields and keep "
        "other sections brief or minimal.\n\n"
        "When using the structured format, populate these fields:\n"
        "- question_repeated: Repeat the student's question exactly.\n"
        "- professor_explanation: Precise, technical explanation.\n"
        "- beginner_explanation: Plain language version.\n"
        "- analogy: Real-world analogy. Omit (null) if not applicable.\n"
        "- theory_and_concepts: Definitions, formulas, rules.\n"
        "- worked_examples: Step-by-step examples.\n"
        "- common_mistakes: Typical student errors. Omit (null) if not applicable.\n"
        "- practice_questions: At least 2 exam-style questions with full answers.\n\n"
        "Course material is provided below. Use it ONLY if it is directly relevant to the question. "
        "If the material is unrelated, ignore it entirely and do not cite it.\n\n"
        "{format_instructions}\n\n"
        "Course material:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_message), MessagesPlaceholder("history"), ("human", "{question}"),])
    return prompt.partial(system_prompt=system_prompt, format_instructions=format_instructions,)
