from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from . import settings

# In-memory storage for conversation history per session
# session_id -> list of (role, content) messages
_conversation_memory: Dict[str, List[tuple[str, str]]] = defaultdict(list)
_memory_lock = threading.Lock()


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




SYSTEM_MESSAGE = """You are a helpful assistant that helps users with their home appliances and furniture by answering questions based on their manuals.

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

6. USE CONVERSATION CONTEXT - If the user refers to previous messages (like "that", "it", "the problem I mentioned"), use the conversation history to understand what they're referring to.

Context from manual:
{context}
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


def _get_conversation_messages(session_id: Optional[str], max_messages: int = 10) -> List:
    """Get conversation history for a session as LangChain messages."""
    if not session_id:
        return []
    
    with _memory_lock:
        if session_id not in _conversation_memory:
            return []
        
        # Get recent messages (last max_messages pairs)
        history = _conversation_memory[session_id][-max_messages:]
        messages = []
        
        for role, content in history:
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        
        return messages


def _add_to_memory(session_id: Optional[str], role: str, content: str):
    """Add a message to conversation memory."""
    if not session_id:
        return
    
    with _memory_lock:
        _conversation_memory[session_id].append((role, content))
        
        # Limit memory size per session (keep last 20 message pairs = 40 messages)
        max_messages = 40
        if len(_conversation_memory[session_id]) > max_messages:
            _conversation_memory[session_id] = _conversation_memory[session_id][-max_messages:]


def clear_session_memory(session_id: Optional[str]):
    """Clear conversation memory for a session."""
    if not session_id:
        return
    
    with _memory_lock:
        if session_id in _conversation_memory:
            del _conversation_memory[session_id]


def answer_question(
    question: str,
    device_id: Optional[str] = None,
    room: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a RAG query with conversation memory and return answer plus structured sources.
    
    Args:
        question: The user's question
        device_id: Optional device ID to filter manuals
        room: Optional room name to filter manuals
        session_id: Optional session ID for conversation memory
    
    Returns:
        Dictionary with 'answer' and 'sources' keys
    """
    retriever = _build_retriever(device_id=device_id, room=room)
    llm = ChatOllama(model=settings.LLM_MODEL_NAME)
    
    # Retrieve documents once and cache for both context and sources
    source_docs = retriever.invoke(question)
    context = _format_docs(source_docs)
    
    # Get conversation history
    chat_history = _get_conversation_messages(session_id)
    
    # Build prompt with system message, history, and current question
    system_msg = SystemMessage(content=SYSTEM_MESSAGE.format(context=context))
    messages = [system_msg]
    
    # Add conversation history
    if chat_history:
        messages.extend(chat_history)
    
    # Add current question
    messages.append(HumanMessage(content=question))
    
    # Generate response
    response = llm.invoke(messages)
    answer = response.content if hasattr(response, 'content') else str(response)
    
    # Add to memory
    _add_to_memory(session_id, "user", question)
    _add_to_memory(session_id, "assistant", answer)
    
    # Build sources from the retrieved documents
    sources = _build_sources_from_docs(source_docs)

    return {"answer": answer, "sources": sources}


