from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from . import settings


def _get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)


def _get_vectorstore() -> Chroma:
    return Chroma(
        persist_directory=str(settings.VECTORDB_DIR),
        embedding_function=_get_embeddings(),
    )


def _build_retriever(device_id: Optional[str], room: Optional[str]):
    vs = _get_vectorstore()
    search_kwargs: Dict[str, Any] = {"k": settings.TOP_K}
    where: Dict[str, Any] = {}

    if device_id:
        where["device_id"] = device_id
    elif room:
        where["room"] = room

    if where:
        search_kwargs["filter"] = where

    return vs.as_retriever(search_kwargs=search_kwargs)




PROMPT_TEMPLATE = """You are a helpful assistant that helps users with their home appliances and furniture by answering questions based on their manuals.

Your approach:
1. UNDERSTAND THE USER'S INTENT - Users may phrase questions informally or use different terminology than the manual. Interpret what they're really asking.

2. USE THE MANUAL AS PRIMARY SOURCE - The context below contains relevant sections from the manual. This is your most reliable information.

3. APPLY COMMON SENSE - Combine manual information with practical knowledge:
   - If the manual explains a feature, you can help troubleshoot related issues
   - If the user describes a problem, connect it to relevant manual sections
   - Use logical reasoning to bridge gaps between what's asked and what's documented

4. BE HELPFUL AND PRACTICAL:
   - Answer in a natural, conversational way
   - Prioritize what the user needs to know to solve their problem
   - If the manual has the exact answer, use it
   - If the manual has related info, adapt it intelligently to the question
   - If the manual is silent, say so, but offer reasonable suggestions based on common sense

5. WHEN INFORMATION IS MISSING:
   - Don't just say "manual doesn't cover this"
   - Offer what you can infer from related sections
   - Suggest reasonable next steps or general best practices
   - Only escalate to "contact manufacturer" if truly necessary

Question: {question}

Context from manual:
{context}

Provide a helpful, practical answer that solves the user's problem:
"""


def _format_docs(docs):
    """Format retrieved documents into context string."""
    return "\n\n".join(doc.page_content for doc in docs)


def _build_sources_from_docs(docs) -> List[Dict[str, Any]]:
    """Extract source metadata from retrieved documents."""
    sources: List[Dict[str, Any]] = []
    for doc in docs:
        meta = doc.metadata or {}
        sources.append(
            {
                "device_id": meta.get("device_id"),
                "device_name": meta.get("device_name"),
                "room": meta.get("room"),
                "brand": meta.get("brand"),
                "model": meta.get("model"),
                "file_name": meta.get("file_name"),
                "page": meta.get("page"),
                "snippet": doc.page_content[:400],
            }
        )
    return sources


def answer_question(
    question: str,
    device_id: Optional[str] = None,
    room: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a RAG query and return answer plus structured sources."""
    retriever = _build_retriever(device_id=device_id, room=room)
    llm = ChatOllama(model=settings.LLM_MODEL_NAME)
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    
    # Retrieve documents once and cache for both context and sources
    source_docs = retriever.invoke(question)
    context = _format_docs(source_docs)
    
    # Build and run the chain with pre-retrieved context
    chain = prompt | llm | StrOutputParser()
    answer: str = chain.invoke({"context": context, "question": question})
    
    # Build sources from the same retrieved documents
    sources = _build_sources_from_docs(source_docs)

    return {"answer": answer, "sources": sources}


