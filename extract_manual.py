"""
Standalone manual extraction tool using DeepSeek-OCR.

Extracts text and images from PDF manuals, with optional translation.

Usage:
    python extract_manual.py <pdf_path> [--debug] [--output-dir <dir>] [--no-translate]

Outputs:
    - {manual_name}_reference.md (always): User-readable reference document
    - {manual_name}_extraction_debug.md (with --debug): Raw OCR output for validation
    - images/ directory: Extracted diagrams and figures
"""

import argparse
from pathlib import Path
from datetime import datetime

from backend.ocr_extraction import extract_pdf_with_ocr
from backend.translation import (
    translate_text,
    detect_language,
    clean_translated_markdown,
)


def generate_debug_md(results: list, pdf_path: Path, output_path: Path):
    """Generate debug markdown with raw OCR output.
    
    Includes page numbers and lists image files for quality validation.
    """
    print(f"\n📝 Generating debug markdown: {output_path.name}")
    
    with output_path.open('w', encoding='utf-8') as f:
        f.write("# Manual Extraction - Debug Output\n\n")
        f.write(f"**Source:** `{pdf_path}`\n\n")
        f.write(f"**Pages extracted:** {len(results)}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("**Purpose:** Quality validation (raw OCR output, original language)\n\n")
        f.write("---\n\n")
        
        for r in results:
            page_num = r['page_num'] + 1
            f.write(f"\n## Page {page_num}\n\n")
            f.write(r['text'])
            f.write('\n\n')
            
            if r['image_files']:
                f.write(f"**Images on this page:** {len(r['image_files'])}\n\n")
                for img_file in r['image_files']:
                    f.write(f"- `{img_file}`\n")
                f.write('\n')
            
            f.write("---\n\n")
    
    print(f"[OK] Debug markdown saved")


def generate_reference_md(
    results: list,
    pdf_path: Path,
    output_path: Path,
    images_dir: Path,
    translate: bool = True,
    skip_index_pages: int = 0,
    translation_model: str | None = None,
):
    """Generate user reference markdown with inline images.
    
    No page numbers, translated to English, images rendered inline.
    """
    print(f"\n[INFO] Generating user reference markdown: {output_path.name}")
    
    # Detect language if translating
    if translate and results:
        sample_text = results[0]["text"]
        detected_lang = detect_language(sample_text, model=translation_model)
        print(f"  Detected language: {detected_lang}")
        
        if detected_lang.lower() == "english":
            print(f"  Text already in English, skipping translation")
            translate = False
    
    # Calculate relative path from output_path to images_dir so that markdown
    # image links work regardless of where the reference file is saved.
    from os import path as _os_path

    images_rel_path = Path(_os_path.relpath(images_dir, output_path.parent))
    
    # Build body content in memory so we can run a second-pass cleanup.
    body_chunks: list[str] = []

    for idx, r in enumerate(results, 1):
        # Optionally skip the first N pages, which are usually the index / TOC
        if idx <= skip_index_pages:
            continue

        text = r["text"]

        # First-pass translation, page-by-page
        if translate:
            if idx % 10 == 1:  # Progress indicator
                print(f"  Translating... ({idx}/{len(results)} pages)")
            text = translate_text(
                text,
                target_lang="English",
                model=translation_model,
            )

        body_chunks.append(text)

        # Insert images inline (generic labels for now)
        if r["image_files"]:
            for img_idx, img_file in enumerate(r["image_files"], 1):
                # TODO: Use vision model for meaningful descriptions
                figure_num = sum(len(res["image_files"]) for res in results[: idx - 1]) + img_idx
                rel_img_path = (images_rel_path / img_file).as_posix()
                body_chunks.append(f"![Figure {figure_num}]({rel_img_path})")

    # Join all chunks and run second-pass cleanup:
    # - Strip leftover ```markdown fences
    # - Remove LLM commentary lines
    # - Re-translate obviously Spanish-heavy paragraphs
    full_body = "\n\n".join(body_chunks)
    full_body = clean_translated_markdown(
        full_body,
        model=translation_model if translate else None,
    )

    with output_path.open("w", encoding="utf-8") as f:
        # Header
        manual_name = pdf_path.stem
        f.write(f"# {manual_name.replace('_', ' ').title()}\n\n")
        f.write(f"**Source:** {pdf_path.name}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}\n\n")

        if translate:
            f.write("**Language:** English (translated)\n\n")

        f.write("---\n\n")

        # Body
        f.write(full_body)
        f.write("\n")
    
    print(f"[OK] Reference markdown saved")


def main():
    parser = argparse.ArgumentParser(
        description="Extract text and images from PDF manuals using OCR"
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to PDF manual"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Generate debug markdown with raw OCR output"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Output directory for markdown files (default: current directory)"
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="Skip translation to English"
    )
    parser.add_argument(
        "--skip-index-pages",
        type=int,
        default=0,
        help="Skip the first N pages when building the reference markdown (useful to drop TOC/index pages)",
    )
    parser.add_argument(
        "--translation-model",
        type=str,
        default=None,
        help="Ollama model name to use for translation (overrides settings.TRANSLATION_MODEL_NAME)",
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return 1
    
    if not pdf_path.suffix.lower() == ".pdf":
        print(f"[ERROR] File must be a PDF: {pdf_path}")
        return 1
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine images directory (same location as PDF)
    images_dir = pdf_path.parent / "images"
    
    # Generate output file names
    manual_name = pdf_path.stem
    debug_md = output_dir / f"{manual_name}_extraction_debug.md"
    reference_md = output_dir / f"{manual_name}_reference.md"
    
    print("=" * 80)
    print("Manual Extraction Tool")
    print("=" * 80)
    print(f"\nPDF: {pdf_path}")
    print(f"Images: {images_dir}")
    print(f"Output: {output_dir}")
    print()
    
    # Step 1: Language Section Detection
    print("[INFO] Scanning PDF for language sections...")
    print()
    
    from backend.language_detection import detect_and_select_language_section, get_language_name
    
    section_info = detect_and_select_language_section(pdf_path, sample_interval=5)
    
    start_page = 0
    end_page = None
    
    if section_info:
        lang_code, start_page, end_page = section_info
        lang_name = get_language_name(lang_code)
        print(f"[OK] Selected {lang_name} section (pages {start_page + 1}-{end_page + 1})")
        print(f"[INFO] Will extract {end_page - start_page + 1} pages")
    else:
        print("[INFO] No clear language sections detected, will extract all pages")
    
    print()
    
    # Step 2: OCR Extraction
    print("[INFO] Starting OCR extraction...")
    print("(This may take several minutes - ~6 seconds per page)")
    print()
    
    try:
        results = extract_pdf_with_ocr(
            pdf_path, 
            images_dir,
            start_page=start_page,
            end_page=end_page
        )
        
        if not results:
            print("\n[ERROR] No pages extracted")
            return 1
        
        print(f"\n[OK] Extracted {len(results)} pages")
        
        # Count images
        total_images = sum(len(r['image_files']) for r in results)        
        print(f"[OK] Extracted {total_images} images")
        
        # Step 2: Generate markdown files
        print("\n" + "=" * 80)
        print("Generating Output Files")
        print("=" * 80)
        
        # Always generate reference MD
        generate_reference_md(
            results,
            pdf_path,
            reference_md,
            images_dir,
            translate=not args.no_translate,
            skip_index_pages=max(args.skip_index_pages, 0),
            translation_model=args.translation_model,
        )
        
        # Optionally generate debug MD
        if args.debug:
            generate_debug_md(results, pdf_path, debug_md)
        
        # Summary
        print("\n" + "=" * 80)        
        print("[OK] EXTRACTION COMPLETE")
        print("=" * 80)
        print(f"\nGenerated files:")        
        print(f"  Reference: {reference_md}")
        if args.debug:
            print(f"  🐛 Debug output: {debug_md}")
        print(f"  🖼️  Images: {images_dir} ({total_images} files)")
        
        print("\n" + "=" * 80)
        print("Next Steps")
        print("=" * 80)
        print(f"1. Review {reference_md.name}")
        print("   - Verify text quality and translation")
        print("   - Check that images are properly placed")
        print()
        print("2. If quality looks good, rebuild vector store:")
        print("   python -m backend.ingest")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

