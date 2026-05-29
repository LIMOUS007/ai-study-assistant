import streamlit as st
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder, PromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableParallel, RunnableLambda
load_dotenv()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
st.set_page_config(page_title="Ai Study Assistant", layout= "wide")
st.title("Ai Study Assistant")
st.markdown("Learn any topic with Ai powered explanations")
topic = st.text_input("Enter a topic", placeholder = "Example: Transformers")
difficulty = st.selectbox("Select difficulty", ["Beginner", "Intermediate", "Advanced"])
style = st.selectbox("Explanation style", ["Conceptual", "Mathematical", "Code-Oriented"])
length = st.selectbox("Explanation Length", ["Short", "Medium", "Detailed"])
temperature = st.slider("creativity", min_value = 0.0, max_value = 1.0, value = 0.5)
class StudyPlan(BaseModel):
    sections: list[str] = Field(description = "List of study sections for topic")
planner_parser = PydanticOutputParser(pydantic_object = StudyPlan)
planner_prompt = PromptTemplate(
template="""
    You are an expert AI tutor.
    Your task is to generate ONLY short section titles for studying a topic.
    Rules:
    - Return ONLY section names
    - Keep each section under 5 words
    - Do NOT include explanations
    - Do NOT include colons
    - Do NOT include bullet points
    Topic: {topic}
    Difficulty: {difficulty}
    Generate 4 useful study sections.
    {format_instructions}
    """,
    input_variables=[
        "topic",
        "difficulty"
    ],
    partial_variables={
        "format_instructions":
        planner_parser.get_format_instructions()
    }
)
prompt = ChatPromptTemplate.from_messages([
    ("system",
    """
    You are an expert AI tutor.
    Your goal is to teach topics clearly and progressively.
    Adjust explanations according to:
    - user difficulty level
    - explanation style
    - requested explanation length
    Use:
    - examples
    - analogies
    - equations when needed
    - code snippets if useful
    Keep explanations accurate and easy to understand.
    """),
        MessagesPlaceholder(variable_name="chat_history"),
    ("human",
    """
    You are generating ONLY ONE section of a larger study guide.
    Main Topic: {topic}
    Current Section: {section}
    Rules:
    - ONLY explain this section
    - Do NOT explain the entire topic
    - Do NOT repeat other sections
    - Stay focused on current section
    Difficulty: {difficulty}
    Style: {style}
    Length: {length}
    """
    )])
model = ChatOpenAI(model = "gpt-4.1-mini", temperature = temperature)
planner_chain = planner_prompt | model | planner_parser
if st.button("Generate explaination"):
    if topic.strip() == "":
        st.warning("Please enter a topic")
    else:
        with st.spinner("Generating explanation..."):
            try:
                studyPlan = planner_chain.invoke({"topic": topic, "difficulty": difficulty})
                if not getattr(studyPlan, "sections", None):
                    st.warning("No sections were generated. Try a different topic or difficulty level.")
                else:
                    parallel_chains = {}
                    section_order = []
                    for idx, section in enumerate(studyPlan.sections, start=1):
                        key = f"section_{idx}"
                        section_order.append((key, section))
                        parallel_chains[key] = (
                            RunnableLambda(lambda x, s=section: {**x, "section": s})
                            | prompt
                            | model
                        )
                    final_chain = RunnableParallel(parallel_chains)
                    results = final_chain.invoke({"topic": topic, "difficulty": difficulty, "style": style, "length": length, "chat_history": st.session_state.chat_history})
                    full_response = ""
                    for key, section in section_order:
                        output = results[key]
                        with st.expander(section):
                            st.markdown(output.content)
                        full_response += (f"\n\n## {section}\n\n{output.content}")
                    st.session_state.chat_history.append(HumanMessage(content = topic))
                    st.session_state.chat_history.append(AIMessage(content = full_response))
            except Exception as e:
                st.error(f"Error: {str(e)}")
            