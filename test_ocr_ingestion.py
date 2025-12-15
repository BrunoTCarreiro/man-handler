"""
Test OCR ingestion on a single manual to validate before full rebuild.
"""

from pathlib import Path
from datetime import datetime
from backend.ocr_extraction import extract_pdf_with_ocr

# Test on LG oven manual
pdf_path = Path("data/manuals/wsed7613s_wsed7613b_wsed7612s_wsed7612b/d814e17fdd75346eb28064f68ada7b17828e151ec076124ea4272726a131d0c4.pdf")
images_dir = Path("data/manuals/wsed7613s_wsed7613b_wsed7612s_wsed7612b/images")

print("=" * 80)
print("Testing OCR Extraction on LG Oven Manual")
print("=" * 80)
print(f"\nPDF: {pdf_path}")
print(f"Images output: {images_dir}")
print("\nStarting extraction...")
print("(This will take a few minutes - ~2-3 seconds per page)")
print()

try:
    results = extract_pdf_with_ocr(pdf_path, images_dir)
    
    # Save full extraction to markdown for inspection
    print("\n" + "=" * 80)
    print("Saving extraction to markdown...")
    print("=" * 80)
    
    output_md = Path("lg_oven_ocr_extraction.md")
    with output_md.open('w', encoding='utf-8') as f:
        f.write("# LG Oven Manual - OCR Extraction\n\n")
        f.write(f"**Source:** `{pdf_path}`\n\n")
        f.write(f"**Pages extracted:** {len(results)}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")
        
        for r in results:
            page_num = r['page_num'] + 1
            f.write(f"\n## Page {page_num}\n\n")
            
            # Write the extracted text
            f.write(r['text'])
            f.write('\n\n')
            
            # Add image references if any
            if r['image_files']:
                f.write(f"**Images on this page:** {len(r['image_files'])}\n\n")
                for img_file in r['image_files']:
                    f.write(f"- `{img_file}`\n")
                f.write('\n')
            
            f.write("---\n\n")
    
    print(f"✓ Full extraction saved to: {output_md}\n")
    
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\nPages extracted: {len(results)}")
    
    # Count total images
    total_images = sum(len(r["image_files"]) for r in results)
    print(f"Images extracted: {total_images}")
    
    # Show sample pages with images
    pages_with_images = [r for r in results if r["image_files"]]
    if pages_with_images:
        print(f"Pages with images: {len(pages_with_images)}")
        print("\nSample pages with images:")
        for r in pages_with_images[:5]:
            print(f"  Page {r['page_num'] + 1}: {len(r['image_files'])} image(s)")
    
    # Show text sample from first page
    if results:
        print("\nSample text from page 1:")
        print("-" * 80)
        sample = results[0]["text"][:500]
        print(sample)
        if len(results[0]["text"]) > 500:
            print("...")
        print("-" * 80)
    
    # Check image directory
    if images_dir.exists():
        image_files = list(images_dir.glob("*.png"))
        print(f"\nImage files saved: {len(image_files)}")
        if image_files:
            print(f"First few: {[f.name for f in sorted(image_files)[:5]]}")
    
    print("\n✓ Test successful!")
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print(f"1. Review the extraction: {output_md}")
    print("   - Check text quality and formatting")
    print("   - Verify tables are properly structured")
    print("   - Confirm no grounding tags remain")
    print("   - Validate image extraction")
    print()
    print("2. If quality looks good:")
    print("   python -m backend.ingest")
    print("   (to rebuild vector store with OCR extraction)")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()





