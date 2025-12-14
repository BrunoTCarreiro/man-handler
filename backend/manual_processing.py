from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langdetect import LangDetectException, detect, detect_langs
from pypdf import PdfReader, PdfWriter
from langchain_ollama import ChatOllama
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    _HAS_REPORTLAB = True
except Exception:  # pragma: no cover - optional dependency at runtime
    # Allow importing the backend even if reportlab isn't installed yet.
    # Functions that require reportlab will raise a clear error when called.
    _HAS_REPORTLAB = False

from . import settings

TEMP_UPLOADS_DIR = settings.DATA_DIR / "_uploads"


def _token_dir(token: str) -> Path:
    return TEMP_UPLOADS_DIR / token


def _meta_path(token: str) -> Path:
    return _token_dir(token) / "meta.json"


def _ensure_temp_dir() -> None:
    TEMP_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _write_meta(token: str, meta: Dict) -> None:
    _ensure_temp_dir()
    _token_dir(token).mkdir(parents=True, exist_ok=True)
    with _meta_path(token).open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def load_meta(token: str) -> Dict:
    path = _meta_path(token)
    if not path.exists():
        raise FileNotFoundError(f"Unknown token: {token}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def register_temp_manual(filename: str, content: bytes) -> Dict:
    """Persist an uploaded manual into a temp directory and return metadata."""
    _ensure_temp_dir()
    token = uuid.uuid4().hex
    upload_dir = _token_dir(token)
    upload_dir.mkdir(parents=True, exist_ok=True)

    sanitized_name = filename.replace(" ", "_")
    target = upload_dir / sanitized_name
    with target.open("wb") as f:
        f.write(content)

    metadata = {
        "token": token,
        "original_filename": sanitized_name,
        "stored_filename": sanitized_name,
        "english_filename": None,
        "extracted_pages": [],
    }
    _write_meta(token, metadata)
    return metadata


def cleanup_token(token: str) -> None:
    """Remove temp artifacts for a token."""
    dir_path = _token_dir(token)
    if dir_path.exists():
        shutil.rmtree(dir_path, ignore_errors=True)


def get_temp_file_path(token: str, filename: str) -> Path:
    """Return the path to a temp file for a token."""
    path = _token_dir(token) / filename
    if not path.exists():
        raise FileNotFoundError(f"File {filename} not found for token {token}")
    return path


def suggest_device_metadata(filename: str, device_id_hint: Optional[str] = None) -> Dict:
    """Generate naive metadata suggestions based on filename and optional hint."""
    stem = Path(filename).stem
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", stem).strip()
    slug_base = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")

    suggested_id = device_id_hint or slug_base or f"device_{uuid.uuid4().hex[:6]}"
    suggested_name = " ".join(word.capitalize() for word in normalized.split())

    return {
        "id": suggested_id,
        "name": suggested_name or suggested_id.replace("_", " ").title(),
        "brand": "",
        "model": "",
        "room": "",
        "category": "",
        "manual_files": [filename],
    }


def _clean_text_for_detection(text: str) -> str:
    text = re.sub(r"https?://\\S+|www\\.\\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\\S+@\\S+", "", text)
    text = re.sub(r"\\b\\d+[x×]\\d+\\b", "", text)
    text = re.sub(r"\\b\\d+[°]\\s*[CF]\\b", "", text)
    text = re.sub(r"\\b\\d+\\s*[VWAh]\\b", "", text)
    text = re.sub(r"\\b\\d{4,}\\b", "", text)
    return text.strip()


def _has_substantial_text(text: str, min_words: int = 15) -> bool:
    words = [w for w in text.split() if len(w) > 2 and not w.isdigit()]
    return len(words) >= min_words


def extract_english_sections(
    input_pdf: Path, output_pdf: Optional[Path] = None
) -> Tuple[List[int], Path]:
    """Extract English-only pages from a PDF."""
    if output_pdf is None:
        output_pdf = input_pdf.with_name(f"{input_pdf.stem}_english{input_pdf.suffix}")

    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    english_pages: List[int] = []

    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if len(text.strip()) < 100:
            continue

        cleaned = _clean_text_for_detection(text)
        if not _has_substantial_text(cleaned):
            continue

        try:
            lang = detect(cleaned)
        except LangDetectException:
            continue

        if lang == "en":
            writer.add_page(page)
            english_pages.append(idx)

    if not english_pages:
        raise ValueError("No English pages detected in manual.")

    with output_pdf.open("wb") as f:
        writer.write(f)

    return english_pages, output_pdf


def run_extraction_for_token(token: str) -> Dict:
    meta = load_meta(token)
    original_path = _token_dir(token) / meta["stored_filename"]
    english_path = (
        _token_dir(token) / f"{Path(meta['stored_filename']).stem}_english.pdf"
    )
    english_pages, output_pdf = extract_english_sections(original_path, english_path)

    meta["english_filename"] = output_pdf.name
    meta["extracted_pages"] = english_pages
    _write_meta(token, meta)
    return {
        "token": token,
        "english_filename": output_pdf.name,
        "english_pages": english_pages,
    }


def update_meta(token: str, **changes) -> Dict:
    meta = load_meta(token)
    meta.update(changes)
    _write_meta(token, meta)
    return meta


def analyze_extracted_manual(token: str) -> Dict:
    """Analyze the extracted manual to suggest device metadata using LLM."""
    meta = load_meta(token)
    
    # Use the original PDF file for analysis (not the markdown reference)
    pdf_filename = meta.get("stored_filename")
    if not pdf_filename:
        raise ValueError("No PDF file available for analysis")
    
    pdf_path = _token_dir(token) / pdf_filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_filename}")
    
    # Extract text from the first few pages of the original PDF
    reader = PdfReader(str(pdf_path))
    text_chunks = []
    max_pages = min(5, len(reader.pages))  # Analyze first 5 pages max
    
    for i in range(max_pages):
        page_text = reader.pages[i].extract_text() or ""
        if page_text.strip():
            text_chunks.append(page_text)
    
    full_text = "\n".join(text_chunks)
    
    # Limit text to first 3000 characters to avoid token limits
    analysis_text = full_text[:3000]
    
    if not analysis_text.strip():
        # Fallback to filename-based suggestion if no text could be extracted
        return suggest_device_metadata(meta["stored_filename"])
    
    # Use LLM to extract device metadata
    llm = ChatOllama(model=settings.LLM_MODEL_NAME, temperature=0)
    
    prompt = f"""You are analyzing a device manual. Extract the following information from the text:
- Device name (the product name)
- Brand/Manufacturer
- Model number
- Category (e.g., "cooker hood", "microwave", "dishwasher", "washing machine", etc.)

Text from manual:
{analysis_text}

Respond ONLY with a JSON object in this exact format (use empty strings if information is not found):
{{
  "name": "device name here",
  "brand": "brand name here",
  "model": "model number here",
  "category": "device category here",
  "room": "room this device is in"
}}"""
    
    def _parse_json_response(text: str) -> Dict:
        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            snippet = text[start_idx:end_idx]
            return json.loads(snippet)
        raise ValueError("No JSON found in LLM response")

    def _build_prompt(text: str) -> str:
        return f"""You are analyzing a device manual. Extract the following information from the text:
- Device name (the product name)
- Brand/Manufacturer
- Model number
- Category (e.g., "cooker hood", "microwave", "dishwasher", "washing machine", etc.)

Text from manual (truncated for brevity):
{text}

Respond ONLY with a JSON object in this exact format (no prose, no code fences). Use empty strings if not found:
{{
  "name": "device name here",
  "brand": "brand name here",
  "model": "model number here",
  "category": "device category here",
  "room": "room this device is in"
}}"""

    llm = ChatOllama(model=settings.LLM_MODEL_NAME, temperature=0)
    prompts = [
        _build_prompt(analysis_text),
        """Return ONLY JSON with keys name, brand, model, category. Use empty strings if unknown.
{
  "name": "",
  "brand": "",
  "model": "",
  "category": "",
  "room": ""
}""",
    ]

    extracted = None
    for prompt in prompts:
        try:
            response = llm.invoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)
            extracted = _parse_json_response(response_text)
            break
        except Exception as e:
            print(f"LLM analysis attempt failed: {e}")

    if not extracted:
        print("LLM analysis failed twice; falling back to filename-based suggestion")
        return suggest_device_metadata(meta["stored_filename"])

    # Heuristic room inference if missing
    def _infer_room(extracted_data: Dict, text: str) -> str:
        room = (extracted_data.get("room") or "").strip().lower()
        if room:
            return room
        combined = " ".join(
            [
                str(extracted_data.get("category") or "").lower(),
                str(extracted_data.get("name") or "").lower(),
                str(extracted_data.get("brand") or "").lower(),
                text.lower(),
            ]
        )
        room_keywords = [
            ("bath", "bathroom"),
            ("towel", "bathroom"),
            ("toilet", "bathroom"),
            ("shower", "bathroom"),
            ("kitchen", "kitchen"),
            ("oven", "kitchen"),
            ("cook", "kitchen"),
            ("laundry", "laundry"),
            ("washer", "laundry"),
            ("washing machine", "laundry"),
            ("dryer", "laundry"),
            ("garage", "garage"),
            ("living", "living room"),
            ("sofa", "living room"),
            ("bedroom", "bedroom"),
            ("bed", "bedroom"),
            ("patio", "outdoor"),
            ("outdoor", "outdoor"),
            ("desk", "office"),
            ("office", "office"),
        ]
        for needle, room_val in room_keywords:
            if needle in combined:
                return room_val
        return ""

    if extracted.get("name") and extracted.get("model"):
        base = f"{extracted['name']} {extracted['model']}"
    elif extracted.get("brand") and extracted.get("model"):
        base = f"{extracted['brand']} {extracted['model']}"
    elif extracted.get("name"):
        base = extracted["name"]
    elif extracted.get("brand"):
        base = extracted["brand"]
    else:
        base = meta["stored_filename"]

    device_id = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")
    device_id = device_id or f"device_{uuid.uuid4().hex[:6]}"

    inferred_room = _infer_room(extracted, analysis_text)

    return {
        "id": device_id,
        "name": extracted.get("name", "").strip(),
        "brand": extracted.get("brand", "").strip(),
        "model": extracted.get("model", "").strip(),
        "category": extracted.get("category", "").strip(),
        "room": inferred_room or extracted.get("room", "").strip(),
        "manual_files": [pdf_filename],
    }


def _detect_language(text: str) -> str:
    """Detect the language of the text."""
    try:
        cleaned = _clean_text_for_detection(text)
        if _has_substantial_text(cleaned):
            return detect(cleaned)
    except LangDetectException:
        pass
    return "unknown"


def _translate_text_chunk(text: str, source_lang: str = "auto") -> str:
    """Translate a text chunk to English using Ollama."""
    llm = ChatOllama(model=settings.TRANSLATION_MODEL_NAME, temperature=0.3)
    
    lang_hint = f" from {source_lang}" if source_lang != "auto" else ""
    
    prompt = f"""Translate the following text{lang_hint} to English. Preserve technical terms, model numbers, and formatting as much as possible. Only output the translation, nothing else.

Text to translate:
{text}

Translation:"""
    
    try:
        response = llm.invoke(prompt)
        translated = response.content if hasattr(response, 'content') else str(response)
        return translated.strip()
    except Exception as e:
        print(f"Translation failed for chunk: {e}")
        return text  # Return original if translation fails


def translate_manual_to_english(token: str) -> Dict:
    """Translate a non-English manual to English using Ollama."""
    if not _HAS_REPORTLAB:
        raise RuntimeError(
            "Missing optional dependency 'reportlab'. Install backend requirements: pip install -r backend/requirements.txt"
        )
    meta = load_meta(token)
    original_path = _token_dir(token) / meta["stored_filename"]
    
    if not original_path.exists():
        raise FileNotFoundError(f"Original PDF not found: {meta['stored_filename']}")
    
    # Read the original PDF
    reader = PdfReader(str(original_path))
    total_pages = len(reader.pages)
    
    # Detect language from first page
    first_page_text = reader.pages[0].extract_text() or ""
    detected_lang = _detect_language(first_page_text)
    
    print(f"Detected language: {detected_lang}")
    
    # Extract and translate text from all pages
    translated_pages = []
    
    for idx, page in enumerate(reader.pages, start=1):
        print(f"Translating page {idx}/{total_pages}...")
        
        text = page.extract_text() or ""
        if len(text.strip()) < 50:
            # Skip pages with very little text
            translated_pages.append(text)
            continue
        
        # Split into smaller chunks if text is very long (to avoid token limits)
        max_chunk_size = 2000
        if len(text) > max_chunk_size:
            # Split by paragraphs/newlines
            chunks = text.split('\n\n')
            translated_chunks = []
            current_chunk = ""
            
            for chunk in chunks:
                if len(current_chunk) + len(chunk) > max_chunk_size and current_chunk:
                    translated_chunks.append(_translate_text_chunk(current_chunk, detected_lang))
                    current_chunk = chunk
                else:
                    current_chunk += "\n\n" + chunk if current_chunk else chunk
            
            if current_chunk:
                translated_chunks.append(_translate_text_chunk(current_chunk, detected_lang))
            
            translated_text = "\n\n".join(translated_chunks)
        else:
            translated_text = _translate_text_chunk(text, detected_lang)
        
        translated_pages.append(translated_text)
    
    # Create a new PDF with translated text
    translated_filename = f"{Path(meta['stored_filename']).stem}_translated_english.pdf"
    translated_path = _token_dir(token) / translated_filename
    
    # Create PDF using ReportLab
    doc = SimpleDocTemplate(
        str(translated_path),
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    for page_num, page_text in enumerate(translated_pages, start=1):
        # Add page number header
        header = Paragraph(f"<b>Page {page_num}</b>", styles['Heading2'])
        story.append(header)
        story.append(Spacer(1, 0.2*inch))
        
        # Add translated text
        # Split into paragraphs and add each
        paragraphs = page_text.split('\n\n')
        for para_text in paragraphs:
            if para_text.strip():
                # Clean up text for ReportLab (escape special chars)
                clean_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                para = Paragraph(clean_text, styles['Normal'])
                story.append(para)
                story.append(Spacer(1, 0.1*inch))
        
        # Add page break except for last page
        if page_num < len(translated_pages):
            story.append(PageBreak())
    
    doc.build(story)
    
    # Update metadata
    meta["translated_filename"] = translated_filename
    meta["detected_language"] = detected_lang
    _write_meta(token, meta)
    
    return {
        "token": token,
        "translated_filename": translated_filename,
        "original_language": detected_lang,
        "pages_translated": total_pages,
    }


def detect_language_for_token(token: str) -> str:
    """Detect language from the first page of the uploaded manual."""
    meta = load_meta(token)
    original_path = _token_dir(token) / meta["stored_filename"]
    if not original_path.exists():
        raise FileNotFoundError(f"Original PDF not found: {meta['stored_filename']}")

    reader = PdfReader(str(original_path))
    if not reader.pages:
        return "unknown"
    first_page_text = reader.pages[0].extract_text() or ""
    return _detect_language(first_page_text)


