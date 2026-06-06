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
    parts = [response.question_repeated, "---", response.professor_explanation,
             response.beginner_explanation]
    if response.analogy:
        parts.append(response.analogy)
    parts += ["---", response.theory_and_concepts, "---", response.worked_examples]
    if response.common_mistakes:
        parts += ["---", response.common_mistakes]
    if response.practice_questions:
        qa_blocks = [
            f"**{i}.** {qa.question}\n\n{qa.answer}"
            for i, qa in enumerate(response.practice_questions, 1)
        ]
        parts += ["---", "\n\n".join(qa_blocks)]
    return "\n\n".join(parts)


def get_academic_parser() -> PydanticOutputParser:
    # TODO: Return a PydanticOutputParser wrapping AcademicResponse.
    # One line:
    #   return PydanticOutputParser(pydantic_object=AcademicResponse)
    raise NotImplementedError("Implement get_academic_parser()")


def build_academic_prompt(system_prompt: str) -> ChatPromptTemplate:
    # TODO: Build the prompt template for structured academic output.
    #
    # Steps:
    #   1. Create the parser: parser = get_academic_parser()
    #   2. Get format instructions: format_instructions = parser.get_format_instructions()
    #   3. Write a system message that:
    #      - Starts with system_prompt (contains course name + course_prompt)
    #      - Instructs the LLM to cover all 9 sections (question_repeated,
    #        professor_explanation, beginner_explanation, analogy, theory_and_concepts,
    #        worked_examples, common_mistakes, practice_questions)
    #      - Ends with: "\n\n{format_instructions}\n\nContext:\n{context}"
    #        (format_instructions is a partial variable, context is injected at runtime)
    #   4. Return a ChatPromptTemplate with:
    #      - ("system", <your system message>)
    #      - MessagesPlaceholder("history")
    #      - ("human", "{question}")
    #
    # Use partial_variables to bake format_instructions in at build time:
    #   ChatPromptTemplate(...).partial(format_instructions=format_instructions)
    raise NotImplementedError("Implement build_academic_prompt()")
