"""
Enhanced ingestion with LLM-powered chunk cleaning.

This version cleans each chunk before embedding to remove:
- Page headers/footers (language indicators, page numbers)
- Boilerplate legal text
- Formatting artifacts
- And translates/normalizes to clean English
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List
import ollama

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document

from . import settings
from .device_catalog import Device, load_devices

logger = logging.getLogger("backend.ingest_enhanced")


CHUNK_CLEANING_PROMPT = """You are a text cleaning assistant. Your job is to take a raw chunk of text from a manual and clean it for semantic search.

INPUT TEXT (may contain noise):
{chunk_text}

YOUR TASK:
1. Remove page headers/footers (e.g., "SPANISH", "ENGLISH", page numbers, dates)
2. Remove language indicators and boilerplate
3. Remove excessive whitespace and formatting artifacts
4. Fix fragmented sentences that were cut off
5. Translate any non-English text to English
6. Keep ONLY the meaningful semantic content
7. If the chunk is about a specific topic, start with a brief context sentence

CRITICAL RULES:
- Output ONLY the cleaned text, no explanations
- Keep all technical terms, model numbers, specifications
- Preserve warnings, cautions, and safety information
- If the chunk contains no meaningful content (just headers/footers), output: [NO CONTENT]
- Be concise but preserve all important information
- Output must be in English

CLEANED TEXT:"""


def clean_chunk_with_llm(chunk_text: str, model: str = "mistral:instruct") -> str:
    """
    Use an LLM to clean and enhance a chunk before embedding.
    
    Args:
        chunk_text: Raw text from PDF chunk
        model: Ollama model to use for cleaning
        
    Returns:
        Cleaned text, or empty string if chunk had no meaningful content
    """
    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': CHUNK_CLEANING_PROMPT.format(chunk_text=chunk_text)
            }],
            options={
                'temperature': 0.1,  # Low temperature for consistent cleaning
                'num_ctx': 4096,
            }
        )
        
        cleaned = response['message']['content'].strip()
        
        # If LLM indicated no content, return empty string
        if cleaned == "[NO CONTENT]" or len(cleaned) < 20:
            return ""
            
        return cleaned
        
    except Exception as e:
        logger.warning("Error cleaning chunk: %s", e)
        # Fall back to original text if cleaning fails
        return chunk_text


def clean_chunks(chunks: List[Document], model: str = "mistral:instruct") -> List[Document]:
    """
    Clean all chunks using an LLM.
    
    Args:
        chunks: List of Document objects with raw text
        model: Ollama model to use
        
    Returns:
        List of Documents with cleaned text (empty content chunks are removed)
    """
    logger.info("Cleaning %d chunks with %s...", len(chunks), model)
    
    cleaned_chunks = []
    skipped = 0
    
    for i, chunk in enumerate(chunks, 1):
        if i % 10 == 0:
            logger.debug("Progress: %d/%d chunks processed (%d skipped)", i, len(chunks), skipped)
        
        original_text = chunk.page_content
        cleaned_text = clean_chunk_with_llm(original_text, model)
        
        if not cleaned_text:
            skipped += 1
            continue
            
        # Create new document with cleaned text but same metadata
        cleaned_chunk = Document(
            page_content=cleaned_text,
            metadata=chunk.metadata
        )
        cleaned_chunks.append(cleaned_chunk)
    
    logger.info("Cleaning complete! Original: %d, Cleaned: %d, Skipped: %d",
                len(chunks), len(cleaned_chunks), skipped)
    
    return cleaned_chunks


def _load_manual_files_for_device(device: Device):
    """Load manual files for a device (same as original ingest.py)"""
    device_dir = settings.MANUALS_DIR / device.id
    for file_name in device.manual_files:
        path = device_dir / file_name
        if not path.exists():
            continue
        if path.suffix.lower() == ".pdf":
            loader = PyPDFLoader(str(path))
        else:
            loader = TextLoader(str(path), encoding="utf-8")
        docs = loader.load()
        for doc in docs:
            doc.metadata.update(
                {
                    "device_id": device.id,
                    "device_name": device.name,
                    "room": device.room,
                    "brand": device.brand,
                    "model": device.model,
                    "category": device.category,
                    "file_name": path.name,
                }
            )
        yield from docs


def load_manuals_with_metadata():
    """Load all manuals with metadata (same as original ingest.py)"""
    devices: List[Device] = load_devices()
    for device in devices:
        yield from _load_manual_files_for_device(device)


def _split_documents(documents):
    """Split documents into chunks (same as original ingest.py)"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def build_vectorstore(clean_chunks_with_llm: bool = True, model: str = "mistral:instruct") -> None:
    """
    Build a fresh Chroma vector store from all manuals.
    
    Args:
        clean_chunks_with_llm: If True, clean chunks with LLM before embedding
        model: Ollama model to use for cleaning
    """
    documents = list(load_manuals_with_metadata())
    if not documents:
        logger.info("No manuals found; skipping vector store build.")
        return

    logger.info("Loaded %d pages from manuals", len(documents))
    
    chunks = _split_documents(documents)
    logger.info("Split into %d chunks", len(chunks))
    
    # NEW: Clean chunks with LLM if enabled
    if clean_chunks_with_llm:
        chunks = clean_chunks(chunks, model)
    
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)

    logger.info("Embedding and storing %d chunks...", len(chunks))
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(settings.VECTORDB_DIR),
    )
    logger.info("Vector store built at %s", settings.VECTORDB_DIR)


def add_device_manuals(device_id: str, clean_chunks_with_llm: bool = True, model: str = "mistral:instruct") -> None:
    """
    Incrementally add manuals for a single device.
    
    Args:
        device_id: Device ID to add
        clean_chunks_with_llm: If True, clean chunks with LLM before embedding
        model: Ollama model to use for cleaning
    """
    from .device_catalog import get_device

    device = get_device(device_id)
    if not device:
        raise ValueError(f"Unknown device_id: {device_id}")

    documents = list(_load_manual_files_for_device(device))
    if not documents:
        logger.info("No manuals found for device %s", device_id)
        return

    chunks = _split_documents(documents)
    
    # NEW: Clean chunks with LLM if enabled
    if clean_chunks_with_llm:
        chunks = clean_chunks(chunks, model)
    
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)

    store = Chroma(
        persist_directory=str(settings.VECTORDB_DIR),
        embedding_function=embeddings,
    )
    store.add_documents(chunks)
    # Note: ChromaDB auto-persists in v0.4+, no need to call persist()
    logger.info("Added manuals for device %s to vector store.", device_id)


if __name__ == "__main__":
    # Build with chunk cleaning enabled
    # This will take longer but produce much cleaner embeddings
    build_vectorstore(clean_chunks_with_llm=True, model="mistral:instruct")
