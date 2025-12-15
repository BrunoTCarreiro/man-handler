from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

from . import settings

logger = logging.getLogger("backend.ingest")
from .device_catalog import Device, load_devices
from .ocr_extraction import extract_pdf_with_ocr


def _load_manual_files_for_device(device: Device):
    """Load manual files for a device.
    
    Prioritizes markdown reference files (processed, clean output).
    Only falls back to PDF extraction if no markdown exists.
    """
    device_dir = settings.MANUALS_DIR / device.id
    
    # Check if there are any markdown reference files for this device
    markdown_files = [f for f in device.manual_files if f.lower().endswith('.md')]
    
    if markdown_files:
        # Use processed markdown files (preferred)
        logger.info("Using markdown reference files for %s", device.id)
        for file_name in markdown_files:
            path = device_dir / file_name
            if not path.exists():
                logger.warning("Markdown file not found: %s", path)
                continue
            
            logger.debug("Processing: %s", file_name)
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if not content.strip():
                    logger.warning("Empty markdown file: %s", file_name)
                    continue
                
                # Create a single document from the entire markdown
                # The splitter will chunk it appropriately later
                doc = Document(
                    page_content=content,
                    metadata={
                        "device_id": device.id,
                        "device_name": device.name,
                        "room": device.room,
                        "brand": device.brand,
                        "model": device.model,
                        "category": device.category,
                        "file_name": path.name,
                        "source_type": "markdown_reference",
                    }
                )
                logger.debug("Loaded markdown (%d chars)", len(content))
                yield doc
                
            except Exception as e:
                logger.warning("Failed to read markdown %s: %s", file_name, e)
                continue
    
    else:
        # No markdown files - fall back to extracting PDFs
        # (This handles legacy manuals or manually added PDFs)
        logger.info("No markdown references found, extracting PDFs for %s", device.id)
        images_dir = device_dir / "images"
        
        for file_name in device.manual_files:
            path = device_dir / file_name
            if not path.exists():
                logger.warning("Manual file not found: %s", path)
                continue
            
            if path.suffix.lower() != ".pdf":
                logger.debug("Skipping non-PDF file: %s", file_name)
                continue
            
            logger.debug("Processing PDF: %s", file_name)
            
            # Extract PDF with OCR (includes image extraction)
            ocr_results = extract_pdf_with_ocr(path, images_dir)
            
            if not ocr_results:
                logger.warning("No pages extracted from %s", file_name)
                continue
            
            logger.debug("Extracted %d pages", len(ocr_results))
            
            # Convert OCR results to Document objects
            for page_data in ocr_results:
                doc = Document(
                    page_content=page_data["text"],
                    metadata={
                        "device_id": device.id,
                        "device_name": device.name,
                        "room": device.room,
                        "brand": device.brand,
                        "model": device.model,
                        "category": device.category,
                        "file_name": path.name,
                        "page": page_data["page_num"] + 1,  # 1-indexed for display
                        "has_images": len(page_data["image_files"]) > 0,
                        "image_files": ",".join(page_data["image_files"]) if page_data["image_files"] else "",
                        "source_type": "pdf_ocr",
                    }
                )
                yield doc


def load_manuals_with_metadata():
    devices: List[Device] = load_devices()
    for device in devices:
        yield from _load_manual_files_for_device(device)


def _split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def build_vectorstore() -> None:
    """Build a fresh Chroma vector store from all manuals."""
    documents = list(load_manuals_with_metadata())
    if not documents:
        logger.info("No manuals found; skipping vector store build.")
        return

    chunks = _split_documents(documents)
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(settings.VECTORDB_DIR),
    )
    logger.info("Vector store built at %s", settings.VECTORDB_DIR)


def add_device_manuals(device_id: str) -> None:
    """Incrementally add manuals for a single device."""
    from .device_catalog import get_device

    device = get_device(device_id)
    if not device:
        raise ValueError(f"Unknown device_id: {device_id}")

    documents = list(_load_manual_files_for_device(device))
    if not documents:
        logger.info("No manuals found for device %s", device_id)
        return

    chunks = _split_documents(documents)
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)

    store = Chroma(
        persist_directory=str(settings.VECTORDB_DIR),
        embedding_function=embeddings,
    )
    store.add_documents(chunks)
    # Note: ChromaDB auto-persists in v0.4+, no need to call persist()
    logger.info("Added manuals for device %s to vector store.", device_id)


def remove_device_from_vectorstore(device_id: str) -> None:
    """Remove all chunks for a specific device from ChromaDB."""
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)
    
    store = Chroma(
        persist_directory=str(settings.VECTORDB_DIR),
        embedding_function=embeddings,
    )
    
    # Delete all documents with matching device_id
    try:
        store.delete(where={"device_id": device_id})
        # Note: ChromaDB auto-persists in v0.4+, no need to call persist()
        logger.info("Removed device '%s' from vector store", device_id)
    except Exception as e:
        logger.warning("Failed to remove device from vector store: %s", e)


def replace_device_manuals(device_id: str) -> None:
    """Replace manuals for a device (delete old, add new)."""
    logger.info("Replacing manuals for device '%s'", device_id)
    
    # Remove old embeddings
    remove_device_from_vectorstore(device_id)
    
    # Add new embeddings
    add_device_manuals(device_id)
    
    logger.info("Successfully replaced manuals for device '%s'", device_id)


if __name__ == "__main__":
    build_vectorstore()


