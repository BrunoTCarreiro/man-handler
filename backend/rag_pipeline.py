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
# session_id -> {"messages": list of (role, content), "last_access": timestamp}
_conversation_memory: Dict[str, Dict[str, Any]] = {}
_memory_lock = threading.Lock()

# Memory management constants
MAX_MESSAGES_PER_SESSION = 40  # Keep last 40 messages (20 pairs)
MAX_SESSIONS = 100  # Maximum number of concurrent sessions
SESSION_TTL_SECONDS = 3600  # 1 hour TTL for inactive sessions

# Cached vectorstore and embeddings (singleton pattern for performance)
_vectorstore: Optional[Chroma] = None
_embeddings: Optional[OllamaEmbeddings] = None
_vectorstore_lock = threading.Lock()


def _get_vectorstore() -> Chroma:
    """Get or create cached vectorstore instance."""
    global _vectorstore, _embeddings
    with _vectorstore_lock:
        if _vectorstore is None:
            # Create embeddings inline to avoid nested lock acquisition
            if _embeddings is None:
                _embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)
            _vectorstore = Chroma(
                persist_directory=str(settings.VECTORDB_DIR),
                embedding_function=_embeddings,
            )
        return _vectorstore


def reload_vectorstore() -> None:
    """Clear cached vectorstore and embeddings.
    
    Call this when:
    - Embedding model changes
    - Database is reset/rebuilt
    - Manual refresh is needed
    """
    global _vectorstore, _embeddings
    with _vectorstore_lock:
        _vectorstore = None
        _embeddings = None


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
    """Format retrieved documents into context string with source headers.
    
    Adds source information for better grounding and to help the model
    avoid mixing information from different devices.
    """
    formatted_chunks = []
    for doc in docs:
        meta = doc.metadata or {}
        device_name = meta.get("device_name", "Unknown device")
        file_name = meta.get("file_name", "Unknown file")
        page = meta.get("page")
        
        # Build source header
        source_header = f"SOURCE: {device_name}"
        if file_name:
            source_header += f" ({file_name})"
        if page:
            source_header += f" - Page {page}"
        
        # Combine header with content
        formatted_chunks.append(f"{source_header}\n{doc.page_content}")
    
    return "\n\n---\n\n".join(formatted_chunks)


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


def _cleanup_expired_sessions():
    """Remove expired sessions based on TTL and enforce max session limit.
    
    Called automatically during memory operations to keep memory bounded.
    """
    import time
    
    with _memory_lock:
        current_time = time.time()
        
        # Remove expired sessions (TTL-based)
        expired = [
            sid for sid, data in _conversation_memory.items()
            if current_time - data.get("last_access", 0) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del _conversation_memory[sid]
        
        # If still over limit, remove oldest sessions
        if len(_conversation_memory) > MAX_SESSIONS:
            sorted_sessions = sorted(
                _conversation_memory.items(),
                key=lambda x: x[1].get("last_access", 0)
            )
            to_remove = len(_conversation_memory) - MAX_SESSIONS
            for sid, _ in sorted_sessions[:to_remove]:
                del _conversation_memory[sid]


def _get_conversation_messages(session_id: Optional[str], max_messages: int = 10) -> List:
    """Get conversation history for a session as LangChain messages."""
    import time
    
    if not session_id:
        return []
    
    with _memory_lock:
        if session_id not in _conversation_memory:
            return []
        
        # Update last access time
        _conversation_memory[session_id]["last_access"] = time.time()
        
        # Get recent messages (last max_messages pairs)
        history = _conversation_memory[session_id]["messages"][-max_messages:]
        messages = []
        
        for role, content in history:
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        
        return messages


def _add_to_memory(session_id: Optional[str], role: str, content: str):
    """Add a message to conversation memory."""
    import time
    
    if not session_id:
        return
    
    with _memory_lock:
        # Initialize session if needed
        if session_id not in _conversation_memory:
            _conversation_memory[session_id] = {
                "messages": [],
                "last_access": time.time()
            }
        
        # Add message
        _conversation_memory[session_id]["messages"].append((role, content))
        _conversation_memory[session_id]["last_access"] = time.time()
        
        # Limit memory size per session
        messages = _conversation_memory[session_id]["messages"]
        if len(messages) > MAX_MESSAGES_PER_SESSION:
            _conversation_memory[session_id]["messages"] = messages[-MAX_MESSAGES_PER_SESSION:]
        
        # Periodic cleanup (every 10th message addition)
        if len(_conversation_memory) > MAX_SESSIONS * 0.8:  # Cleanup when 80% full
            _cleanup_expired_sessions()


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


