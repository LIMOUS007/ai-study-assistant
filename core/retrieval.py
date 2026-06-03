import httpx
from pathlib import Path
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
def _format_docs(docs):
    parts = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        page_str = f", page {page}" if page != "" else ""
        parts.append(f"[Source: {source}{page_str}]\n{doc.page_content}")
    return "\n\n".join(parts)
def build_rag_chain(course_id: str, system_prompt: str):
    embeddings = OpenAIEmbeddings(http_client=httpx.Client(verify=False))
    vectorstore_path = Path("vectorstore") / course_id
    vector_store = Chroma(embedding_function=embeddings, persist_directory=str(vectorstore_path))  
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt + "\n\nAnswer using only the context below. Cite sources.\n\n{context}"), MessagesPlaceholder("history"), ("human", "{question}"),])
    model = ChatOpenAI(model="gpt-4.1-mini", http_client=httpx.Client(verify=False))
    chain = RunnableParallel(context = RunnableLambda(lambda x: x["question"]) | retriever | RunnableLambda(_format_docs),
                             history = RunnableLambda(lambda x: x["history"]), 
                             question = RunnableLambda(lambda x: x["question"])) | prompt | model | StrOutputParser()
    return chain