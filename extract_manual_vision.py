import json
import ollama
from pathlib import Path
import base64
from io import BytesIO

SCHEMA = """{
  "device_metadata": {
    "device_id": "wsed7613s_wsed7613b_wsed7612s_wsed7612b",
    "brand": "LG Electronics",
    "model": "WSED7613S",
    "category": "oven",
    "manual_language": "es"
  },
  "specifications": {},
  "installation": {},
  "operations": [],
  "cooking_modes": [],
  "maintenance": [],
  "troubleshooting": [],
  "safety_warnings": [],
  "error_codes": [],
  "recipes_or_cooking_guides": [],
  "warranty": {},
  "accessories": []
}"""

VISION_EXTRACTION_PROMPT = """You are analyzing pages from an LG oven manual to extract structured information. The manual is in Spanish, but **you MUST output everything in English only**.

CRITICAL RULES:
1. OUTPUT ONLY IN ENGLISH - Translate everything from Spanish to English
2. Describe visual elements: diagrams, control panel layouts, button symbols, icons
3. Extract both text and visual information from the pages
4. Return valid JSON only, no explanatory text

For each batch of pages, extract:

**Operations & Cooking Modes:**
- Identify cooking mode symbols/icons and describe them
- Note button layouts and control panel instructions
- Extract step-by-step procedures

**Maintenance:**
- Look for cleaning diagrams and procedures
- Identify visual instructions (arrows, numbered steps in images)
- Note what parts are shown in diagrams

**Troubleshooting:**
- Extract problem-solution pairs
- Note any diagnostic flowcharts or visual guides

**Safety Warnings:**
- Look for warning symbols (⚠️, 🔥, ⚡, etc.)
- Extract all safety-related content

**Error Codes:**
- Look for error code tables or displays
- Note what error displays look like

**Specifications & Installation:**
- Extract dimensions from diagrams
- Note installation clearances from technical drawings
- Identify electrical connection diagrams

Return a JSON object that adds to this schema structure. Use snake_case for IDs. Be thorough with visual descriptions.

REMEMBER: ALL OUTPUT MUST BE IN ENGLISH, NOT SPANISH."""


def pdf_pages_to_images(pdf_path, start_page=0, end_page=None, dpi=150):
    """Convert PDF pages to PIL Images."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("❌ Error: PyMuPDF not installed. Run: pip install pymupdf")
        return []
    
    doc = fitz.open(pdf_path)
    images = []
    
    if end_page is None:
        end_page = len(doc)
    
    for page_num in range(start_page, min(end_page, len(doc))):
        page = doc[page_num]
        # Render page to image (higher DPI = better quality but slower)
        pix = page.get_pixmap(dpi=dpi)
        img_data = pix.tobytes("png")
        images.append({
            'page_num': page_num + 1,
            'data': img_data
        })
    
    return images, len(doc)


def analyze_page_with_vision(image_data, page_num, model="llama3.2-vision:11b"):
    """Send single page image to vision model for analysis."""
    
    # Encode image for Ollama
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    prompt = f"""{VISION_EXTRACTION_PROMPT}

Analyzing page {page_num} of the manual. Extract all relevant information from this page.

Return partial JSON with the fields you found information for. Empty fields can be omitted.
OUTPUT IN ENGLISH ONLY. NO SPANISH."""

    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_b64]
            }],
            options={
                'temperature': 0.1,
                'num_ctx': 8192,
            }
        )
        
        result = response['message']['content']
        return result
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None


def merge_extractions(base, new_data):
    """Merge new extraction data into base structure."""
    if not new_data:
        return base
    
    # Merge arrays (operations, maintenance, etc.)
    for key in ['operations', 'cooking_modes', 'maintenance', 'troubleshooting', 
                'safety_warnings', 'error_codes', 'recipes_or_cooking_guides', 'accessories']:
        if key in new_data and isinstance(new_data[key], list):
            if key not in base:
                base[key] = []
            base[key].extend(new_data[key])
    
    # Merge objects (specifications, installation, warranty)
    for key in ['specifications', 'installation', 'warranty']:
        if key in new_data and isinstance(new_data[key], dict):
            if key not in base:
                base[key] = {}
            base[key].update(new_data[key])
    
    return base


def extract_with_vision(pdf_path, model="llama3.2-vision:11b", skip_pages=0, max_pages=None):
    """Extract structured data from PDF using vision model."""
    
    print(f"\n{'='*60}")
    print(f"Vision-Based Manual Extraction")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"PDF: {pdf_path}")
    print(f"Strategy: Processing one page at a time (vision model limitation)")
    
    # Convert PDF to images
    print(f"\n📄 Converting PDF pages to images...")
    all_images, total_pages = pdf_pages_to_images(pdf_path)
    print(f"✓ Converted {total_pages} pages")
    
    # Limit pages if specified
    if skip_pages > 0:
        all_images = all_images[skip_pages:]
        print(f"⏩ Skipping first {skip_pages} pages")
    
    if max_pages:
        all_images = all_images[:max_pages]
        print(f"📌 Processing only {max_pages} pages")
    
    # Initialize result structure
    result = json.loads(SCHEMA)
    
    # Process page by page
    all_responses = []
    
    print(f"\n🤖 Processing {len(all_images)} pages (this will take a while)...")
    print(f"   Estimated time: ~{len(all_images) * 0.5:.0f}-{len(all_images) * 1:.0f} minutes\n")
    
    for idx, img_data in enumerate(all_images):
        page_num = img_data['page_num']
        
        print(f"[{idx + 1}/{len(all_images)}] Page {page_num}...", end=" ", flush=True)
        
        response = analyze_page_with_vision(img_data['data'], page_num, model)
        
        if response:
            print(f"✓ ({len(response)} chars)")
            
            # Save individual page response
            page_file = f"extraction_page_{page_num:03d}.txt"
            with open(page_file, "w", encoding="utf-8") as f:
                f.write(f"=== Page {page_num} ===\n\n")
                f.write(response)
            all_responses.append(response)
            
            # Try to parse and merge
            try:
                cleaned = response.strip()
                if cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    lines = lines[1:]
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    cleaned = '\n'.join(lines)
                
                page_data = json.loads(cleaned)
                result = merge_extractions(result, page_data)
            except json.JSONDecodeError:
                pass  # Some pages might not have structured data
        else:
            print("❌ Failed")
    
    # Save all responses combined
    with open("extraction_all_pages.txt", "w", encoding="utf-8") as f:
        f.write("\n\n=== PAGE SEPARATOR ===\n\n".join(all_responses))
    
    return result


if __name__ == "__main__":
    pdf_path = "data/manuals/wsed7613s_wsed7613b_wsed7612s_wsed7612b/d814e17fdd75346eb28064f68ada7b17828e151ec076124ea4272726a131d0c4.pdf"
    
    # Check if PDF exists
    if not Path(pdf_path).exists():
        print(f"❌ Error: PDF not found at {pdf_path}")
        exit(1)
    
    # Extract using vision
    print("\nStarting vision-based extraction...")
    print("This will process the manual page-by-page, seeing diagrams and images.")
    print("Estimated time: 48-96 minutes for 96 pages.\n")
    
    # For initial testing, processing pages 5-10:
    data = extract_with_vision(pdf_path, model="llama3.2-vision:11b", skip_pages=5, max_pages=5)
    
    # To process all pages, uncomment this instead:
    # data = extract_with_vision(pdf_path, model="llama3.2-vision:11b")
    
    # Save final result
    output_path = "data/catalog/lg_oven_structured.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ EXTRACTION COMPLETE!")
    print(f"{'='*60}")
    print(f"Output saved to: {output_path}")
    print(f"Individual page responses saved as: extraction_page_NNN.txt")
    print(f"\nNext steps:")
    print(f"  1. Review {output_path} for completeness")
    print(f"  2. Check that visual elements were described")
    print(f"  3. Verify everything is in English")
    print(f"  4. Refine schema based on what was extracted")
    print(f"{'='*60}\n")

