"""
Test DeepSeek-OCR on sample manual pages.

This script:
1. Extracts pages from LG oven manual as images
2. Tests DeepSeek-OCR with different prompts
3. Compares output to current PyMuPDF extraction
4. Saves results for review
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict
import fitz  # PyMuPDF
import ollama
from PIL import Image, ImageDraw, ImageFont

# Configuration
PDF_PATH = "data/manuals/wsed7613s_wsed7613b_wsed7612s_wsed7612b/d814e17fdd75346eb28064f68ada7b17828e151ec076124ea4272726a131d0c4.pdf"
OUTPUT_DIR = Path("ocr_test_results")
TEST_PAGES = [10, 25, 50]  # Test a few diverse pages

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_page_as_image(pdf_path: str, page_num: int, output_path: Path) -> bool:
    """Extract a single page from PDF as PNG image."""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render page to image at 1x resolution to match DeepSeek-OCR coordinate system
        # The model/Ollama resizes images anyway, so 2x just causes coordinate misalignment
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
        pix.save(output_path)
        
        doc.close()
        return True
    except Exception as e:
        print(f"Error extracting page {page_num}: {e}")
        return False

def get_pymupdf_text(pdf_path: str, page_num: int) -> str:
    """Get current PyMuPDF text extraction for comparison."""
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        text = page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"Error: {e}"

def test_deepseek_ocr(image_path: Path, prompt: str) -> str:
    """Run DeepSeek-OCR on an image with given prompt."""
    try:
        # Read the image file and encode as base64
        import base64
        with open(image_path, 'rb') as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        # Use the proper Ollama vision API with images parameter
        response = ollama.chat(
            model='deepseek-ocr:3b',
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]  # Pass image as base64
            }],
            options={
                'temperature': 0.1,  # Low temperature for consistent extraction
            }
        )
        
        return response['message']['content']
    except Exception as e:
        return f"Error: {e}"

def parse_grounding_output(grounding_text: str, scale_x: float = 1.0, scale_y: float = 1.0) -> List[Dict]:
    """
    Parse grounding output to extract element types and coordinates.
    Returns list of dicts: [{'type': 'image', 'coords': [x1, y1, x2, y2], 'index': N}, ...]
    
    Args:
        grounding_text: Raw grounding output text
        scale_x: X-axis scale factor to apply to coordinates
        scale_y: Y-axis scale factor to apply to coordinates
    """
    elements = []
    
    # Pattern: <|ref|>TYPE<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>
    pattern = r'<\|ref\|>(\w+)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>'
    
    matches = re.finditer(pattern, grounding_text)
    
    for idx, match in enumerate(matches):
        element_type = match.group(1)
        x1, y1, x2, y2 = int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5))
        
        # Apply scale factors to coordinates
        x1_scaled = int(x1 * scale_x)
        y1_scaled = int(y1 * scale_y)
        x2_scaled = int(x2 * scale_x)
        y2_scaled = int(y2 * scale_y)
        
        # Filter for images and figures only
        if element_type.lower() in ['image', 'figure']:
            elements.append({
                'type': element_type,
                'coords': [x1_scaled, y1_scaled, x2_scaled, y2_scaled],
                'index': len([e for e in elements if e['type'].lower() in ['image', 'figure']]) + 1,
                'y_position': y1_scaled  # Top y-coordinate for sorting
            })
    
    # Sort by y-position (top to bottom)
    elements.sort(key=lambda x: x['y_position'])
    
    # Renumber indices after sorting
    for idx, elem in enumerate(elements, 1):
        elem['index'] = idx
    
    return elements

def extract_image_region(page_image_path: Path, coords: List[int], output_path: Path) -> bool:
    """
    Crop image region from page PNG using bounding box coordinates.
    
    Args:
        page_image_path: Path to the full page PNG
        coords: [x1, y1, x2, y2] bounding box coordinates
        output_path: Where to save the cropped image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Open the page image
        img = Image.open(page_image_path)
        
        # Crop using coordinates: (left, top, right, bottom)
        x1, y1, x2, y2 = coords
        cropped = img.crop((x1, y1, x2, y2))
        
        # Save the cropped image
        cropped.save(output_path)
        
        return True
    except Exception as e:
        print(f"  ⚠️  Error extracting image region: {e}")
        return False

def calculate_ollama_scale(original_width: int, original_height: int, model_size: int = 1000) -> tuple[float, float]:
    """
    Calculate how Ollama scales images - it resizes to exactly model_size x model_size.
    
    Ollama resizes all images to 1000x1000 regardless of aspect ratio.
    This means the image is stretched/squashed to fit the square.
    
    Returns:
        (scale_x, scale_y): Scale factors to convert model coordinates back to original image
    """
    # Simple direct scaling from 1000x1000 back to original dimensions
    scale_x = original_width / model_size
    scale_y = original_height / model_size
    
    return scale_x, scale_y

def create_debug_visualization(page_image_path: Path, grounding_text: str, output_path: Path) -> bool:
    """
    Create a debug image with rectangles drawn over detected elements.
    
    Args:
        page_image_path: Path to the full page PNG
        grounding_text: Raw grounding output text
        output_path: Where to save the debug visualization
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Open the page image
        img = Image.open(page_image_path)
        draw = ImageDraw.Draw(img)
        
        # Print dimensions for debugging
        print(f"  DEBUG: Original image dimensions: {img.width} x {img.height}")
        
        # Calculate scale factors based on Ollama's 1024x1024 resizing
        scale_x, scale_y = calculate_ollama_scale(img.width, img.height)
        print(f"  DEBUG: Calculated scale factors: X={scale_x:.3f}, Y={scale_y:.3f}")
        
        # Parse ALL elements (not just images)
        pattern = r'<\|ref\|>(\w+)<\|/ref\|><\|det\|>\[\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\]<\|/det\|>'
        matches = list(re.finditer(pattern, grounding_text))
        
        if matches:
            all_x = []
            all_y = []
            for match in matches:
                x1, y1, x2, y2 = int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5))
                all_x.extend([x1, x2])
                all_y.extend([y1, y2])
            print(f"  DEBUG: Model coordinate ranges - X: {min(all_x)}-{max(all_x)}, Y: {min(all_y)}-{max(all_y)}")
        
        # Color map for different element types
        colors = {
            'image': 'red',
            'figure': 'red',
            'table': 'blue',
            'text': 'green',
            'title': 'purple',
            'header': 'orange',
        }
        
        for match in matches:
            element_type = match.group(1).lower()
            x1, y1, x2, y2 = int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5))
            
            # Apply scale factors to coordinates
            x1_scaled = int(x1 * scale_x)
            y1_scaled = int(y1 * scale_y)
            x2_scaled = int(x2 * scale_x)
            y2_scaled = int(y2 * scale_y)
            
            # Choose color based on type
            color = colors.get(element_type, 'yellow')
            
            # Draw rectangle with scaled coordinates
            draw.rectangle([x1_scaled, y1_scaled, x2_scaled, y2_scaled], outline=color, width=3)
            
            # Draw label with scaled coordinates
            label = f"{element_type}"
            # Draw text background
            draw.rectangle([x1_scaled, y1_scaled-20, x1_scaled+100, y1_scaled], fill=color)
            draw.text((x1_scaled+5, y1_scaled-15), label, fill='white')
        
        # Save debug image
        img.save(output_path)
        return True
        
    except Exception as e:
        print(f"  ⚠️  Error creating debug visualization: {e}")
        return False

def integrate_images_into_markdown(text_output: str, images: List[Dict], page_num: int) -> str:
    """
    Insert markdown image references into text output.
    
    Strategy: Append images at the end with section headers.
    This is simpler and more reliable than trying to position based on y-coordinates.
    
    Args:
        text_output: The markdown text from prompt 1
        images: List of image dicts with 'type', 'coords', 'index'
        page_num: Page number for generating image filenames
        
    Returns:
        Enhanced markdown with image references
    """
    if not images:
        return text_output
    
    # Add images section at the end
    enhanced = text_output.rstrip() + "\n\n"
    enhanced += "---\n\n"
    enhanced += "## Figures and Diagrams\n\n"
    
    for img in images:
        img_filename = f"page_{page_num:03d}_image_{img['index']}.png"
        enhanced += f"![{img['type'].capitalize()} {img['index']}]({img_filename})\n\n"
    
    return enhanced

def main():
    """Main test routine."""
    print("="*80)
    print("DeepSeek-OCR Test")
    print("="*80)
    
    # Skip model check - just try to use it
    print("\n1. Starting OCR test (assuming deepseek-ocr:3b is available)...")
    print("   If model is missing, you'll see an error when we try to use it.")
    print("   To download: ollama pull deepseek-ocr:3b")
    
    # Test different prompts
    prompts = [
        "Extract the text in the image.",
        "<|grounding|>Convert the document to markdown.",
        "<|grounding|>Return the layout of the image.",
    ]
    
    results = []
    
    for page_num in TEST_PAGES:
        print(f"\n{'='*80}")
        print(f"Testing Page {page_num}")
        print(f"{'='*80}")
        
        # Extract page as image
        image_path = OUTPUT_DIR / f"page_{page_num:03d}.png"
        print(f"\n2. Extracting page {page_num} as image...")
        
        if not extract_page_as_image(PDF_PATH, page_num, image_path):
            print(f"❌ Failed to extract page {page_num}")
            continue
        
        print(f"✅ Saved to {image_path}")
        
        # Get PyMuPDF baseline
        print(f"\n3. Getting PyMuPDF baseline extraction...")
        pymupdf_text = get_pymupdf_text(PDF_PATH, page_num)
        
        baseline_path = OUTPUT_DIR / f"page_{page_num:03d}_pymupdf.txt"
        with open(baseline_path, 'w', encoding='utf-8') as f:
            f.write(pymupdf_text)
        
        print(f"✅ Baseline: {len(pymupdf_text)} chars")
        
        # Store OCR results for this page
        page_ocr_results = {}
        
        # Test each OCR prompt
        for i, prompt in enumerate(prompts, 1):
            print(f"\n4.{i} Testing OCR with prompt: '{prompt}'")
            
            ocr_text = test_deepseek_ocr(image_path, prompt)
            
            # Save result
            result_path = OUTPUT_DIR / f"page_{page_num:03d}_ocr_prompt{i}.txt"
            with open(result_path, 'w', encoding='utf-8') as f:
                f.write(f"PROMPT: {prompt}\n")
                f.write("="*80 + "\n\n")
                f.write(ocr_text)
            
            print(f"✅ OCR Result: {len(ocr_text)} chars → {result_path}")
            
            # Store results by prompt index
            page_ocr_results[i] = ocr_text
            
            results.append({
                'page': page_num,
                'prompt': prompt,
                'pymupdf_len': len(pymupdf_text),
                'ocr_len': len(ocr_text),
                'result_file': result_path
            })
        
        # NEW: Process grounding output and integrate images
        print(f"\n5. Processing image integration...")
        
        # Parse grounding output (prompt 3)
        grounding_output = page_ocr_results.get(3, "")
        
        # Create debug visualization and get scale factors
        debug_path = OUTPUT_DIR / f"page_{page_num:03d}_debug.png"
        if create_debug_visualization(image_path, grounding_output, debug_path):
            print(f"  ✅ Created debug visualization → {debug_path.name}")
        
        # Calculate scale factors based on Ollama's 1024x1024 resizing
        img = Image.open(image_path)
        scale_x, scale_y = calculate_ollama_scale(img.width, img.height)
        
        images = parse_grounding_output(grounding_output, scale_x, scale_y)
        
        if images:
            print(f"  ✅ Found {len(images)} image(s) on page {page_num}")
            
            # Extract each image region
            extracted_count = 0
            for img in images:
                img_output_path = OUTPUT_DIR / f"page_{page_num:03d}_image_{img['index']}.png"
                if extract_image_region(image_path, img['coords'], img_output_path):
                    print(f"  ✅ Extracted image {img['index']} → {img_output_path.name}")
                    extracted_count += 1
                else:
                    print(f"  ❌ Failed to extract image {img['index']}")
            
            # Integrate images into prompt 1 text output
            if extracted_count > 0:
                text_output = page_ocr_results.get(1, "")
                integrated_text = integrate_images_into_markdown(text_output, images, page_num)
                
                # Save integrated output
                integrated_path = OUTPUT_DIR / f"page_{page_num:03d}_ocr_integrated.txt"
                with open(integrated_path, 'w', encoding='utf-8') as f:
                    f.write(f"INTEGRATED OUTPUT (Text + Images)\n")
                    f.write("="*80 + "\n\n")
                    f.write(integrated_text)
                
                print(f"  ✅ Saved integrated output → {integrated_path.name}")
        else:
            print(f"  ℹ️  No images found on page {page_num}")
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("TEST COMPLETE - Summary Report")
    print(f"{'='*80}\n")
    
    summary_path = OUTPUT_DIR / "SUMMARY.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("DeepSeek-OCR Test Results\n")
        f.write("="*80 + "\n\n")
        
        f.write("Pages Tested:\n")
        for page in TEST_PAGES:
            f.write(f"  - Page {page}\n")
        
        f.write(f"\nPrompts Tested:\n")
        for i, prompt in enumerate(prompts, 1):
            f.write(f"  {i}. {prompt}\n")
        
        f.write(f"\n{'='*80}\n")
        f.write("RESULTS BY PAGE\n")
        f.write(f"{'='*80}\n\n")
        
        for page_num in TEST_PAGES:
            page_results = [r for r in results if r['page'] == page_num]
            if not page_results:
                continue
                
            f.write(f"\nPage {page_num}:\n")
            f.write(f"  PyMuPDF baseline: {page_results[0]['pymupdf_len']} chars\n")
            
            for r in page_results:
                f.write(f"  OCR (prompt {prompts.index(r['prompt'])+1}): {r['ocr_len']} chars\n")
            
            f.write(f"\n  Files:\n")
            f.write(f"    - page_{page_num:03d}_pymupdf.txt (baseline)\n")
            for i in range(len(prompts)):
                f.write(f"    - page_{page_num:03d}_ocr_prompt{i+1}.txt\n")
            
            # Check if integrated output exists
            integrated_file = OUTPUT_DIR / f"page_{page_num:03d}_ocr_integrated.txt"
            if integrated_file.exists():
                f.write(f"    - page_{page_num:03d}_ocr_integrated.txt (text + images)\n")
                # List image files
                image_files = list(OUTPUT_DIR.glob(f"page_{page_num:03d}_image_*.png"))
                for img_file in sorted(image_files):
                    f.write(f"    - {img_file.name}\n")
        
        f.write(f"\n{'='*80}\n")
        f.write("EVALUATION CRITERIA\n")
        f.write(f"{'='*80}\n\n")
        f.write("Compare the OCR results to PyMuPDF baseline:\n\n")
        f.write("✅ GOOD if OCR:\n")
        f.write("  - Preserves table structure better (markdown format)\n")
        f.write("  - Maintains layout information\n")
        f.write("  - Removes headers/footers more cleanly\n")
        f.write("  - Produces more semantic/readable output\n\n")
        f.write("❌ BAD if OCR:\n")
        f.write("  - Loses important information\n")
        f.write("  - Hallucinations or errors\n")
        f.write("  - Significantly longer/more verbose\n")
        f.write("  - Doesn't handle tables well\n\n")
        f.write("➡️ NEXT STEPS:\n")
        f.write("  1. Review the output files in ocr_test_results/\n")
        f.write("  2. Compare OCR to PyMuPDF for each page\n")
        f.write("  3. Decide which prompt works best\n")
        f.write("  4. If OCR is better → Create ADR-006 for OCR extraction\n")
        f.write("  5. If OCR is worse → Consider other approaches\n")
    
    print(f"✅ Summary saved to {summary_path}")
    print(f"\nAll results saved to: {OUTPUT_DIR}/")
    print("\nReview the files to compare OCR vs PyMuPDF extraction:")
    print(f"  - cd {OUTPUT_DIR}")
    print(f"  - Start with SUMMARY.txt")
    print(f"  - Then compare page_XXX_pymupdf.txt vs page_XXX_ocr_promptX.txt")

if __name__ == "__main__":
    main()
