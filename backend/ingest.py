from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

from . import settings
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
        print(f"\n[INFO] Using markdown reference files for {device.id}")
        for file_name in markdown_files:
            path = device_dir / file_name
            if not path.exists():
                print(f"  Warning: File not found: {path}")
                continue
            
            print(f"  Processing: {file_name}")
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if not content.strip():
                    print(f"  Warning: Empty markdown file: {file_name}")
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
                print(f"  [OK] Loaded markdown ({len(content)} chars)")
                yield doc
                
            except Exception as e:
                print(f"  Warning: Failed to read markdown {file_name}: {e}")
                continue
    
    else:
        # No markdown files - fall back to extracting PDFs
        # (This handles legacy manuals or manually added PDFs)
        print(f"\n[INFO] No markdown references found, extracting PDFs for {device.id}")
        images_dir = device_dir / "images"
        
        for file_name in device.manual_files:
            path = device_dir / file_name
            if not path.exists():
                print(f"  Warning: File not found: {path}")
                continue
            
            if path.suffix.lower() != ".pdf":
                print(f"  Skipping non-PDF file: {file_name}")
                continue
            
            print(f"  Processing PDF: {file_name}")
            
            # Extract PDF with OCR (includes image extraction)
            ocr_results = extract_pdf_with_ocr(path, images_dir)
            
            if not ocr_results:
                print(f"  Warning: No pages extracted from {file_name}")
                continue
            
            print(f"  [OK] Extracted {len(ocr_results)} pages")
            
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
        print("No manuals found; skipping vector store build.")
        return

    chunks = _split_documents(documents)
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(settings.VECTORDB_DIR),
    )
    print(f"Vector store built at {settings.VECTORDB_DIR}")


def add_device_manuals(device_id: str) -> None:
    """Incrementally add manuals for a single device."""
    from .device_catalog import get_device

    device = get_device(device_id)
    if not device:
        raise ValueError(f"Unknown device_id: {device_id}")

    documents = list(_load_manual_files_for_device(device))
    if not documents:
        print(f"No manuals found for device {device_id}")
        return

    chunks = _split_documents(documents)
    embeddings = OllamaEmbeddings(model=settings.EMBED_MODEL_NAME)

    store = Chroma(
        persist_directory=str(settings.VECTORDB_DIR),
        embedding_function=embeddings,
    )
    store.add_documents(chunks)
    store.persist()
    print(f"Added manuals for device {device_id} to vector store.")


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
        store.persist()
        print(f"[OK] Removed device '{device_id}' from vector store")
    except Exception as e:
        print(f"[WARN] Failed to remove device from vector store: {e}")


def replace_device_manuals(device_id: str) -> None:
    """Replace manuals for a device (delete old, add new)."""
    print(f"[INFO] Replacing manuals for device '{device_id}'")
    
    # Remove old embeddings
    remove_device_from_vectorstore(device_id)
    
    # Add new embeddings
    add_device_manuals(device_id)
    
    print(f"[OK] Successfully replaced manuals for device '{device_id}'")


if __name__ == "__main__":
    build_vectorstore()


