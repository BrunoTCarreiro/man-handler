from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel, Field

from . import manual_processing, settings
from .device_catalog import Device, get_device, list_rooms, load_devices, save_devices
from .ingest import add_device_manuals, remove_device_from_vectorstore, replace_device_manuals
from .rag_pipeline import answer_question
from .ocr_extraction import extract_pdf_with_ocr
from extract_manual import generate_reference_md
from .translation import detect_language
from .language_detection import detect_and_select_language_section, get_language_name

# Global dict to store processing status for polling
processing_status: Dict[str, Dict] = {}

# Global dict to store cancellation flags
cancellation_flags: Dict[str, bool] = {}

# Lock for thread-safe access to processing_status
status_lock = threading.Lock()

# TTL for processing status entries (1 hour in seconds)
STATUS_TTL_SECONDS = 3600


def cleanup_expired_statuses() -> None:
    """Remove processing status entries older than TTL."""
    current_time = time.time()
    with status_lock:
        expired_tokens = [
            token for token, status in processing_status.items()
            if current_time - status.get("created_at", 0) > STATUS_TTL_SECONDS
        ]
        for token in expired_tokens:
            del processing_status[token]
            if token in cancellation_flags:
                del cancellation_flags[token]
        if expired_tokens:
            logger.info("Cleaned up %d expired processing status entries", len(expired_tokens))


class ChatRequest(BaseModel):
    message: str
    device_id: Optional[str] = None
    room: Optional[str] = None
    session_id: Optional[str] = None


class Source(BaseModel):
    device_id: Optional[str]
    device_name: Optional[str]
    room: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    file_name: str
    page: Optional[int] = None
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]


class ManualMetadata(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    room: Optional[str] = None
    category: Optional[str] = None
    manual_files: List[str] = Field(default_factory=list)


class ManualExtractResponse(BaseModel):
    token: str
    original_filename: str
    english_filename: str
    english_pages: List[int]


class ManualTranslateResponse(BaseModel):
    token: str
    original_filename: str
    translated_filename: str
    original_language: str
    pages_translated: int


class ManualAnalyzeRequest(BaseModel):
    token: str


class ManualAnalyzeResponse(BaseModel):
    token: str
    suggested_metadata: ManualMetadata


class ManualProcessResponse(BaseModel):
    token: str
    detected_language: str
    translated: bool
    output_filename: str
    pages: List[int] | None = None
    logs: List[str] = Field(default_factory=list)


class ManualCommitRequest(BaseModel):
    token: str
    metadata: ManualMetadata
    manual_filename: str


class ManualCommitResponse(BaseModel):
    device: Device


app = FastAPI(title="Home Manual Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get logger from settings
logger = settings.logger


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/devices", response_model=List[Device])
def list_devices() -> List[Device]:
    return load_devices()


@app.get("/devices/{device_id}", response_model=Device)
def get_device_details(device_id: str) -> Device:
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.get("/rooms", response_model=List[str])
def get_rooms() -> List[str]:
    return list_rooms()


@app.post("/manuals/extract", response_model=ManualExtractResponse)
async def extract_manual(file: UploadFile = File(...)) -> ManualExtractResponse:
    """Step 1a: Upload file and extract English pages."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Register and extract in one step
    temp_meta = manual_processing.register_temp_manual(file.filename, content)
    try:
        result = manual_processing.run_extraction_for_token(temp_meta["token"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    return ManualExtractResponse(
        token=result["token"],
        original_filename=temp_meta["stored_filename"],
        english_filename=result["english_filename"],
        english_pages=result["english_pages"],
    )


@app.post("/manuals/translate", response_model=ManualTranslateResponse)
async def translate_manual(file: UploadFile = File(...)) -> ManualTranslateResponse:
    """Step 1b: Upload file and translate to English."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Register the manual
    temp_meta = manual_processing.register_temp_manual(file.filename, content)
    
    try:
        result = manual_processing.translate_manual_to_english(temp_meta["token"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}") from exc
    
    return ManualTranslateResponse(
        token=result["token"],
        original_filename=temp_meta["stored_filename"],
        translated_filename=result["translated_filename"],
        original_language=result["original_language"],
        pages_translated=result["pages_translated"],
    )


def process_manual_background(token: str, pdf_path: Path, images_dir: Path, reference_md: Path):
    """Background task to process manual with cancellation support."""
    
    def add_log(message: str) -> None:
        """Thread-safe log addition."""
        with status_lock:
            if token in processing_status:
                processing_status[token]["logs"].append(message)
    
    def check_cancelled() -> bool:
        """Check if processing has been cancelled."""
        return cancellation_flags.get(token, False)
    
    def progress_cb(page_idx: int, total: int) -> None:
        if check_cancelled():
            return
        log_msg = f"[OK] Page {page_idx}/{total} processed"
        add_log(log_msg)
    
    try:
        # Pre-scan for language sections
        add_log("[INFO] Scanning PDF for language sections...")
        with status_lock:
            if token in processing_status:
                processing_status[token]["stage"] = "language_scan"
        
        section_info = detect_and_select_language_section(pdf_path, sample_interval=2)
        
        if check_cancelled():
            add_log("[INFO] Processing cancelled by user")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["status"] = "cancelled"
                    processing_status[token]["stage"] = "cancelled"
            return
        
        # Determine extraction parameters
        start_page = 0
        end_page = None
        detected_language = "unknown"
        
        if section_info:
            detected_language, start_page, end_page = section_info
            lang_name = get_language_name(detected_language)
            add_log(f"[OK] Found {lang_name} section (pages {start_page + 1}-{end_page + 1})")
            add_log(f"[INFO] Will extract {end_page - start_page + 1} pages instead of entire PDF")
        else:
            add_log("[INFO] No clear language sections detected, will extract all pages")
        
        # OCR extract pages + images (only selected section)
        add_log("[INFO] Starting OCR extraction...")
        with status_lock:
            if token in processing_status:
                processing_status[token]["stage"] = "ocr_extraction"
        
        results = extract_pdf_with_ocr(
            pdf_path, 
            images_dir, 
            progress_callback=progress_cb,
            cancellation_check=lambda: check_cancelled(),
            start_page=start_page,
            end_page=end_page
        )
        
        if check_cancelled():
            add_log("[INFO] Processing cancelled by user")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["status"] = "cancelled"
                    processing_status[token]["stage"] = "cancelled"
            return
        
        if not results:
            raise ValueError("OCR extraction returned no pages")
        
        add_log(f"[OK] Extracted {len(results)} pages")
        with status_lock:
            if token in processing_status:
                processing_status[token]["stage"] = "ocr_complete"

        # If we didn't detect language during pre-scan, detect it now
        if detected_language == "unknown" and results:
            add_log("[INFO] Detecting language from extracted content...")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["stage"] = "language_detection"
            
            detected_language = detect_language(results[0]["text"]) if results else "unknown"
            add_log(f"[OK] Detected language: {detected_language}")
        else:
            lang_name = get_language_name(detected_language)
            add_log(f"[INFO] Using pre-scanned language: {lang_name}")

        if check_cancelled():
            add_log("[INFO] Processing cancelled by user")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["status"] = "cancelled"
                    processing_status[token]["stage"] = "cancelled"
            return

        # Generate reference markdown with inline images; auto-translates if not English
        # Check for both language code "en" and word "english"
        is_english = detected_language.lower() in ["en", "english"]
        
        if not is_english:
            lang_name = get_language_name(detected_language)
            add_log(f"[INFO] Translating from {lang_name} to English...")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["stage"] = "translating"
        else:
            add_log("[INFO] Text already in English, generating reference markdown...")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["stage"] = "generating_reference"
        
        generate_reference_md(
            results,
            pdf_path,
            reference_md,
            images_dir,
            translate=not is_english,
            skip_index_pages=0,
            translation_model=None,
        )
        
        if check_cancelled():
            add_log("[INFO] Processing cancelled by user")
            with status_lock:
                if token in processing_status:
                    processing_status[token]["status"] = "cancelled"
                    processing_status[token]["stage"] = "cancelled"
            return
        
        add_log("[OK] Reference markdown generated")
        
        with status_lock:
            if token in processing_status:
                processing_status[token]["stage"] = "complete"
                processing_status[token]["status"] = "complete"
                processing_status[token]["detected_language"] = detected_language
                processing_status[token]["translated"] = not is_english
                processing_status[token]["output_filename"] = reference_md.name
        
        # Persist reference filename and detected language
        try:
            manual_processing.update_meta(
                token,
                translated_filename=reference_md.name,
                detected_language=detected_language,
            )
        except Exception:
            pass
            
    except Exception as exc:
        with status_lock:
            if token in processing_status:
                processing_status[token]["status"] = "error"
                processing_status[token]["stage"] = "error"
                processing_status[token]["logs"].append(f"[ERROR] {str(exc)}")
    finally:
        # Cleanup cancellation flag
        if token in cancellation_flags:
            del cancellation_flags[token]


@app.post("/manuals/process", response_model=ManualProcessResponse)
async def process_manual(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> ManualProcessResponse:
    """Unified flow using the OCR pipeline (extract_manual): OCR + detect + translate as needed.
    
    This endpoint returns immediately with a token, then processes in the background.
    Use GET /manuals/process/status/{token} to poll for progress.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Register upload in temp
    temp_meta = manual_processing.register_temp_manual(file.filename, content)
    token = temp_meta["token"]
    pdf_path = manual_processing.get_temp_file_path(token, temp_meta["stored_filename"])
    images_dir = pdf_path.parent / "images"
    reference_md = pdf_path.parent / f"{pdf_path.stem}_reference.md"

    # Initialize status tracking
    with status_lock:
        processing_status[token] = {
            "status": "processing",
            "logs": ["[INFO] Upload received, starting processing..."],
            "stage": "starting",
            "created_at": time.time(),
        }
        cancellation_flags[token] = False

    # Start background processing
    background_tasks.add_task(
        process_manual_background,
        token,
        pdf_path,
        images_dir,
        reference_md
    )
    
    # Return immediately with token
    return ManualProcessResponse(
        token=token,
        detected_language="processing",
        translated=False,
        output_filename="",
        pages=None,
        logs=["[INFO] Processing started in background. Poll /manuals/process/status/{token} for updates."],
    )


@app.get("/manuals/process/status/{token}")
def get_processing_status(token: str):
    """Get current processing status for a manual upload token.
    
    Returns real-time logs and status during processing, enabling
    the frontend to poll for progress updates.
    """
    # Periodically cleanup expired entries
    cleanup_expired_statuses()
    
    if token not in processing_status:
        # Return a default "not found" status instead of 404 to avoid breaking the UI
        return {
            "status": "error",
            "logs": ["[ERROR] Processing status not found. Token may have expired."],
            "stage": "error"
        }
    
    with status_lock:
        return dict(processing_status[token])


@app.post("/manuals/process/cancel/{token}")
def cancel_processing(token: str):
    """Cancel an in-progress manual processing task.
    
    Sets the cancellation flag which will be checked between operations.
    The processing will stop at the next checkpoint (usually between pages).
    """
    if token not in cancellation_flags:
        raise HTTPException(status_code=404, detail="Token not found or already completed")
    
    cancellation_flags[token] = True
    
    with status_lock:
        if token in processing_status:
            processing_status[token]["logs"].append("[INFO] Cancellation requested...")
    
    return {"status": "cancelling", "message": "Cancellation requested. Processing will stop at next checkpoint."}


@app.post("/manuals/analyze", response_model=ManualAnalyzeResponse)
def analyze_manual(request: ManualAnalyzeRequest) -> ManualAnalyzeResponse:
    """Step 2: Analyze extracted PDF to suggest device metadata."""
    try:
        suggestions = manual_processing.analyze_extracted_manual(request.token)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    
    return ManualAnalyzeResponse(
        token=request.token,
        suggested_metadata=ManualMetadata(**suggestions),
    )


@app.post("/manuals/commit", response_model=ManualCommitResponse)
def commit_manual(request: ManualCommitRequest) -> ManualCommitResponse:
    """Step 3: Commit the manual to the knowledge base."""
    try:
        temp_meta = manual_processing.load_meta(request.token)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    manual_filename = request.manual_filename
    try:
        source_path = manual_processing.get_temp_file_path(request.token, manual_filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    target_dir = settings.MANUALS_DIR / request.metadata.id
    target_dir.mkdir(parents=True, exist_ok=True)
    destination_path = target_dir / manual_filename

    shutil.move(source_path, destination_path)

    # If images directory exists alongside the temp file, move it as well
    images_dir = source_path.parent / "images"
    if images_dir.exists() and images_dir.is_dir():
        target_images_dir = target_dir / "images"
        if target_images_dir.exists():
            shutil.rmtree(target_images_dir, ignore_errors=True)
        shutil.move(str(images_dir), str(target_images_dir))

    devices = load_devices()
    existing = next((d for d in devices if d.id == request.metadata.id), None)

    updated_manual_files = set(existing.manual_files if existing else [])
    updated_manual_files.add(manual_filename)

    device_data = request.metadata.model_dump()
    device_data["manual_files"] = sorted(updated_manual_files)
    device_model = Device(**device_data)

    if existing:
        devices = [device_model if d.id == device_model.id else d for d in devices]
    else:
        devices.append(device_model)

    save_devices(devices)

    try:
        add_device_manuals(device_model.id)
    except Exception as exc:  # pragma: no cover - depends on runtime env
        raise HTTPException(
            status_code=500, detail=f"Failed to update vector store: {exc}"
        ) from exc
    finally:
        manual_processing.cleanup_token(request.token)

    return ManualCommitResponse(device=device_model)


@app.delete("/devices/{device_id}")
def delete_device(device_id: str) -> dict:
    """Delete a device and all its manuals from the system."""
    devices = load_devices()
    device = next((d for d in devices if d.id == device_id), None)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    # Remove from vector store
    try:
        remove_device_from_vectorstore(device_id)
    except Exception as exc:
        logger.warning("Failed to remove from vector store: %s", exc)
    
    # Remove device directory with all files
    device_dir = settings.MANUALS_DIR / device_id
    if device_dir.exists():
        shutil.rmtree(device_dir, ignore_errors=True)
        logger.info("Removed device directory: %s", device_dir)
    
    # Remove from devices.json
    devices = [d for d in devices if d.id != device_id]
    save_devices(devices)
    
    logger.info("Deleted device '%s' successfully", device_id)
    return {"status": "ok", "message": f"Device '{device_id}' deleted successfully"}


@app.post("/devices/{device_id}/replace")
def replace_device_manual(device_id: str) -> dict:
    """Replace manual for an existing device (re-ingest from current files)."""
    device = get_device(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    try:
        replace_device_manuals(device_id)
        return {"status": "ok", "message": f"Manual for device '{device_id}' replaced successfully"}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to replace manual: {exc}"
        ) from exc


class DeviceUpdateRequest(BaseModel):
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    room: Optional[str] = None
    category: Optional[str] = None


@app.patch("/devices/{device_id}")
def update_device(device_id: str, request: DeviceUpdateRequest) -> Device:
    """Update device metadata."""
    devices = load_devices()
    device = next((d for d in devices if d.id == device_id), None)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    # Update metadata
    device.name = request.name
    device.brand = request.brand
    device.model = request.model
    device.room = request.room
    device.category = request.category
    
    # Save updated devices list
    save_devices(devices)
    
    logger.info("Updated device '%s' metadata", device_id)
    return device


class RenameRoomRequest(BaseModel):
    old_room: str
    new_room: str


@app.post("/devices/rooms/rename")
def rename_room(request: RenameRoomRequest) -> dict:
    """Rename a room for all devices in that room."""
    devices = load_devices()
    
    old_room = request.old_room if request.old_room != "Uncategorized" else None
    new_room = request.new_room.strip() or None
    
    # Update room for all devices in the old room
    updated_count = 0
    for device in devices:
        device_room = device.room or None
        if (old_room is None and device_room is None) or (device_room == old_room):
            device.room = new_room
            updated_count += 1
    
    # Save updated devices list
    save_devices(devices)
    
    logger.info("Renamed room '%s' to '%s' (%d devices updated)", request.old_room, request.new_room, updated_count)
    return {
        "status": "ok",
        "message": f"Room renamed successfully",
        "devices_updated": updated_count
    }


@app.get("/devices/{device_id}/markdown", response_class=PlainTextResponse)
def get_device_markdown(device_id: str) -> str:
    """Get the markdown reference file content for a device."""
    devices = load_devices()
    device = next((d for d in devices if d.id == device_id), None)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    device_dir = settings.MANUALS_DIR / device_id
    
    # Look for markdown files
    markdown_files = list(device_dir.glob("*.md"))
    
    if not markdown_files:
        raise HTTPException(
            status_code=404, 
            detail=f"No markdown file found for device {device_id}"
        )
    
    # Return the first (or only) markdown file
    md_file = markdown_files[0]
    
    try:
        content = md_file.read_text(encoding="utf-8")
        logger.debug("Serving markdown for device '%s': %s", device_id, md_file.name)
        return content
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read markdown file: {exc}"
        ) from exc


@app.get("/devices/{device_id}/files/{file_path:path}")
def get_device_file(device_id: str, file_path: str):
    """Serve files (especially images) from device directories."""
    devices = load_devices()
    device = next((d for d in devices if d.id == device_id), None)
    
    if not device:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    
    # Construct the full file path
    device_dir = settings.MANUALS_DIR / device_id
    full_path = device_dir / file_path
    
    # Security check: ensure the file is within the device directory
    try:
        full_path = full_path.resolve()
        device_dir = device_dir.resolve()
        if not str(full_path).startswith(str(device_dir)):
            raise HTTPException(status_code=403, detail="Access forbidden")
    except Exception:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    # Check if file exists
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    logger.debug("Serving file for device '%s': %s", device_id, file_path)
    return FileResponse(full_path)


@app.post("/reset")
def reset_workspace() -> dict:
    """Reset generated artifacts (destructive)."""
    # Clear processing status dict to avoid stale data
    global processing_status
    processing_status.clear()
    
    root = Path(__file__).resolve().parent.parent
    script = root / "tools" / "reset_workspace.py"
    if not script.exists():
        raise HTTPException(status_code=500, detail="Reset script not found")
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            check=True,
            capture_output=True,
            text=True,
        )
        return {"status": "ok", "output": completed.stdout}
    except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime
        raise HTTPException(
            status_code=500, detail=f"Reset failed: {exc.stderr or exc.stdout}"
        ) from exc


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = answer_question(
        question=request.message,
        device_id=request.device_id,
        room=request.room,
    )
    sources = [Source(**s) for s in result["sources"]]
    return ChatResponse(answer=result["answer"], sources=sources)


@app.post("/upload-manual")
async def upload_manual(device_id: str, file: UploadFile = File(...)) -> dict:
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id is required")

    devices = load_devices()
    device = next((d for d in devices if d.id == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device_dir = settings.MANUALS_DIR / device_id
    device_dir.mkdir(parents=True, exist_ok=True)

    dest_path = device_dir / file.filename
    content = await file.read()
    dest_path.write_bytes(content)

    if file.filename not in device.manual_files:
        device.manual_files.append(file.filename)
        save_devices(devices)

    try:
        add_device_manuals(device_id)
    except Exception as exc:  # pragma: no cover - runtime/infra issues
        raise HTTPException(
            status_code=500, detail=f"Failed to update vector store: {exc}"
        ) from exc

    return {"status": "ok", "device_id": device_id, "file": file.filename}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


