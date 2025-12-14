"""
OCR extraction using DeepSeek-OCR for manual processing.

This module uses DeepSeek-OCR via Ollama to extract structured text and images
from PDF pages with better quality than plain PyMuPDF text extraction.

Uses Prompt 2: "<|grounding|>Convert the document to markdown."
- Single call per page (efficient)
- Returns complete markdown text WITH embedded coordinates
- Best text quality according to testing
"""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
import ollama
from PIL import Image


def extract_page_as_image(pdf_path: str | Path, page_num: int, output_path: Path) -> bool:
    """Extract a single page from a PDF as a PNG image.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        output_path: Where to save the PNG

    Returns:
        True if successful, False otherwise.
    """
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]

        # Render page to image at 2x resolution for clearer extracted figures.
        # DeepSeek-OCR (via Ollama) always resizes the image to its internal
        # 1000x1000 space before producing coordinates; we convert those
        # coordinates back using the actual image width/height, so using a
        # higher-resolution render here simply yields sharper crops while
        # keeping alignment correct.
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        pix.save(str(output_path))

        doc.close()
        return True
    except Exception as e:
        print(f"Error extracting page {page_num}: {e}")
        return False


def ocr_page_with_grounding(image_path: Path) -> str:
    """Run DeepSeek-OCR with Prompt 2 (grounding + markdown).

    This prompt returns complete markdown text WITH embedded coordinate tags
    in a single call – best quality and efficiency.

    Args:
        image_path: Path to the page PNG image

    Returns:
        Raw OCR output with grounding tags embedded.
    """
    # Read and encode image as base64
    with image_path.open("rb") as img_file:
        image_data = base64.b64encode(img_file.read()).decode("utf-8")

    # Prompt 2: best combination of text + layout grounding
    response = ollama.chat(
        model="deepseek-ocr:3b",
        messages=[
            {
                "role": "user",
                "content": "<|grounding|>Convert the document to markdown.",
                "images": [image_data],
            }
        ],
        options={
            "temperature": 0.1,  # Low temperature for consistent extraction
        },
    )

    return response["message"]["content"]


def calculate_ollama_scale(
    original_width: int, original_height: int, model_size: int = 1000
) -> Tuple[float, float]:
    """Calculate scale factors to transform model coordinates back to original image.

    Ollama resizes all images to model_size x model_size (1000x1000) regardless
    of aspect ratio. The model outputs coordinates in this 1000x1000 space.

    Args:
        original_width: Original image width
        original_height: Original image height
        model_size: Ollama's resize target (default 1000)

    Returns:
        (scale_x, scale_y): Scale factors for coordinate transformation.
    """
    scale_x = original_width / model_size
    scale_y = original_height / model_size
    return scale_x, scale_y


def parse_grounding_output(
    grounding_text: str, scale_x: float = 1.0, scale_y: float = 1.0
) -> List[Dict]:
    """Parse grounding tags to extract image/figure coordinates.

    Format:
        <|ref|>TYPE<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>

    Args:
        grounding_text: Raw grounding output with embedded tags
        scale_x: X-axis scale factor to apply to coordinates
        scale_y: Y-axis scale factor to apply to coordinates

    Returns:
        List of image elements:
        [{'type': str, 'coords': [x1, y1, x2, y2], 'index': int}, ...]
    """
    elements: List[Dict] = []

    pattern = (
        r"<\|ref\|>(\w+)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>"
    )

    matches = re.finditer(pattern, grounding_text)

    for match in matches:
        element_type = match.group(1)
        x1, y1, x2, y2 = (
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            int(match.group(5)),
        )

        # Apply scale factors to coordinates
        x1_scaled = int(x1 * scale_x)
        y1_scaled = int(y1 * scale_y)
        x2_scaled = int(x2 * scale_x)
        y2_scaled = int(y2 * scale_y)

        # Filter for images and figures only
        if element_type.lower() in ["image", "figure"]:
            elements.append(
                {
                    "type": element_type,
                    "coords": [x1_scaled, y1_scaled, x2_scaled, y2_scaled],
                    "index": len(
                        [e for e in elements if e["type"].lower() in ["image", "figure"]]
                    )
                    + 1,
                    "y_position": y1_scaled,  # For sorting top-to-bottom
                }
            )

    # Sort by y-position (top to bottom)
    elements.sort(key=lambda x: x["y_position"])

    # Renumber indices after sorting
    for idx, elem in enumerate(elements, 1):
        elem["index"] = idx

    return elements


def extract_image_region(page_image_path: Path, coords: List[int], output_path: Path) -> bool:
    """Crop and save an image region from the page PNG.

    Args:
        page_image_path: Path to the full page PNG
        coords: [x1, y1, x2, y2] bounding box coordinates
        output_path: Where to save the cropped image

    Returns:
        True if successful, False otherwise.
    """
    try:
        img = Image.open(page_image_path)
        x1, y1, x2, y2 = coords
        cropped = img.crop((x1, y1, x2, y2))
        cropped.save(output_path)
        return True
    except Exception as e:
        print(f"  Warning: Failed to extract image region: {e}")
        return False


def clean_grounding_tags(text: str) -> str:
    """Remove grounding tags from markdown text before storage.

    Strips patterns like:
        <|ref|>TYPE<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
    and any stray <|...|> tags, leaving only the readable markdown.
    """
    # Remove grounding tag patterns
    pattern = (
        r"<\|ref\|>\w+<\|/ref\|><\|det\|>\[\[\d+,\s*\d+,\s*\d+,\s*\d+\]\]<\|/det\|>\s*"
    )
    cleaned = re.sub(pattern, "", text)

    # Remove any remaining standalone tags like <|ref|>, <|/ref|>, etc.
    cleaned = re.sub(r"<\|[^>]+\|>", "", cleaned)

    return cleaned.strip()


def extract_page_with_ocr(
    pdf_path: str | Path,
    page_num: int,
    images_dir: Path,
) -> Optional[Dict]:
    """Extract a single page using OCR with image extraction.

    This is the main entry point for OCR-based page extraction.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        images_dir: Directory where images for this manual are stored

    Returns:
        {
            'text': str,              # Clean markdown text
            'page_num': int,          # Page number (0-indexed)
            'image_files': List[str]  # List of saved image filenames (relative)
        }
        or None if extraction fails.
    """
    images_dir.mkdir(parents=True, exist_ok=True)

    # Render page image (temporary for processing)
    page_image_name = f"page_{page_num+1:03d}_temp.png"
    page_image_path = images_dir / page_image_name
    
    try:
        if not extract_page_as_image(pdf_path, page_num, page_image_path):
            return None

        # Run OCR with Prompt 2 (single call: markdown + grounding)
        raw_output = ocr_page_with_grounding(page_image_path)

        # Calculate scale factors based on Ollama's 1000x1000 resizing
        # Use context manager to ensure file is closed before cleanup
        with Image.open(page_image_path) as img:
            scale_x, scale_y = calculate_ollama_scale(img.width, img.height)

        # Parse grounding output to find images
        image_elements = parse_grounding_output(raw_output, scale_x, scale_y)

        # Extract image regions
        image_filenames: List[str] = []
        for elem in image_elements:
            img_filename = f"page_{page_num+1:03d}_image_{elem['index']}.png"
            img_output_path = images_dir / img_filename
            if extract_image_region(page_image_path, elem["coords"], img_output_path):
                image_filenames.append(img_filename)

        # Clean grounding tags from text
        clean_text = clean_grounding_tags(raw_output)

        return {
            "text": clean_text,
            "page_num": page_num,
            "image_files": image_filenames,
        }
    
    finally:
        # Clean up temporary page image
        if page_image_path.exists():
            page_image_path.unlink()


def extract_pdf_with_ocr(
    pdf_path: str | Path,
    images_dir: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cancellation_check: Optional[Callable[[], bool]] = None,
    start_page: int = 0,
    end_page: int | None = None,
) -> List[Dict]:
    """Extract pages from a PDF using DeepSeek-OCR.

    Args:
        pdf_path: Path to the PDF file
        images_dir: Directory where images for this manual are stored
        progress_callback: Optional callback for progress updates
        cancellation_check: Optional callback that returns True if processing should stop
        start_page: First page to extract (0-indexed, inclusive)
        end_page: Last page to extract (0-indexed, inclusive). None means extract to end.

    Returns:
        List of per-page results (see extract_page_with_ocr).
    """
    results: List[Dict] = []

    try:
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return results

    # Determine page range
    actual_end_page = end_page if end_page is not None else page_count - 1
    actual_end_page = min(actual_end_page, page_count - 1)
    
    if start_page >= page_count:
        print(f"  [WARN] Start page {start_page} is beyond document length {page_count}")
        return results
    
    pages_to_extract = actual_end_page - start_page + 1
    print(f"  Extracting pages {start_page + 1}-{actual_end_page + 1} ({pages_to_extract} pages) with OCR...")
    
    for page_index in range(start_page, actual_end_page + 1):
        # Check for cancellation before processing each page
        if cancellation_check and cancellation_check():
            print(f"    [INFO] Processing cancelled at page {page_index + 1}/{actual_end_page + 1}")
            break
        
        # Print progress for every page
        current_progress = page_index - start_page + 1
        print(f"    Processing page {page_index + 1} ({current_progress}/{pages_to_extract})...")
        
        page_result = extract_page_with_ocr(pdf_path, page_index, images_dir)
        if page_result is None:
            print(f"    [WARN] Failed to extract page {page_index + 1}")
            continue
        
        print(f"    [OK] Page {page_index + 1} complete ({current_progress}/{pages_to_extract})")
        results.append(page_result)
        
        if progress_callback:
            try:
                progress_callback(current_progress, pages_to_extract)
            except Exception:
                pass

    return results

