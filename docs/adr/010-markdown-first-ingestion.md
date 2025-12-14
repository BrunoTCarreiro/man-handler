# ADR-010: Markdown-First Ingestion Strategy

**Status:** Accepted  
**Date:** 2025-12-13  
**Decision makers:** Development Team  

## Context

The manual processing pipeline (ADR-007) creates cleaned, processed markdown reference files as its primary output. These files:
- ✅ Are already extracted via OCR
- ✅ Have been language-detected
- ✅ Are translated to English (if needed)
- ✅ Contain clean, structured content
- ✅ Include inline image references

However, the original ingestion logic in `backend/ingest.py` was designed before the processing pipeline existed. It would:
1. Look for PDF files only
2. Re-extract them with OCR
3. Process each page individually

**The problem:** Markdown reference files were being **completely ignored**, resulting in:
- ❌ Manuals not appearing in RAG results
- ❌ Wasted processing time (double OCR extraction)
- ❌ Lower quality (re-extracting instead of using cleaned output)

## Decision

We will implement a **markdown-first ingestion strategy** that prioritizes processed markdown files over raw PDFs.

### Ingestion Priority

**1. Check for Markdown Files First**
```python
markdown_files = [f for f in device.manual_files if f.endswith('.md')]

if markdown_files:
    # Use processed markdown (preferred)
    for md_file in markdown_files:
        content = read_markdown(md_file)
        yield Document(content, metadata)
```

**2. Fall Back to PDF Extraction**
```python
else:
    # No markdown - extract PDFs (legacy/manual uploads)
    for pdf_file in device.manual_files:
        results = extract_pdf_with_ocr(pdf_file)
        yield Documents(results)
```

### Architecture Changes

**Modified:** `backend/ingest.py` - `_load_manual_files_for_device()`

**Logic Flow:**
1. Check if device has any `.md` files
2. If YES → Read markdown files, skip PDFs entirely
3. If NO → Extract PDFs with OCR (legacy behavior)

**Why skip PDFs when markdown exists?**
- Markdown is the processed output OF the PDF
- Re-extracting PDF would duplicate work
- Markdown has better quality (cleaned, translated)

## File Types Handled

### Markdown Files (`.md`)
**Source:** Manual processing pipeline output  
**Handling:**
- Read entire file as single document
- Text splitter chunks it appropriately
- Metadata includes device info + `source_type: "markdown_reference"`

**Example:**
```
data/manuals/desk_001/
  └── desk-English_reference.md  ← Ingested
```

### PDF Files (`.pdf`)
**Source:** Legacy manuals or manual uploads without processing  
**Handling:**
- Extract with OCR page-by-page
- Each page becomes a document
- Metadata includes page numbers + `source_type: "pdf_ocr"`

**Example (no markdown exists):**
```
data/manuals/old_device/
  └── manual.pdf  ← Extracted with OCR
```

## Example Output

### With Markdown (Normal Flow)
```
[INFO] Using markdown reference files for desk_001
  Processing: desk-English_reference.md
  [OK] Loaded markdown (45000 chars)
Added manuals for device desk_001 to vector store.
```

### Without Markdown (Legacy Fallback)
```
[INFO] No markdown references found, extracting PDFs for old_device
  Processing PDF: manual.pdf
  [OK] Extracted 50 pages
Added manuals for device old_device to vector store.
```

## Benefits

### Efficiency
- ✅ No double OCR extraction
- ✅ Use already-processed content
- ✅ Faster ingestion (read file vs extract PDF)

### Quality
- ✅ Cleaned content (processed output)
- ✅ Already translated to English
- ✅ Structured markdown format
- ✅ Better chunking (continuous text vs per-page)

### Consistency
- ✅ RAG searches the same content users see in reference
- ✅ Single source of truth (the markdown)
- ✅ No divergence between reference and vector DB

## Document Metadata

### Markdown Documents
```python
{
    "device_id": "desk_001",
    "device_name": "Standing Desk Pro",
    "room": "office",
    "brand": "ErgoDesk",
    "model": "EP-200",
    "category": "furniture",
    "file_name": "desk-English_reference.md",
    "source_type": "markdown_reference"
}
```

### PDF Documents (Legacy)
```python
{
    "device_id": "old_device",
    "device_name": "Old Microwave",
    "room": "kitchen",
    "brand": "LG",
    "model": "LMV1831ST",
    "category": "microwave",
    "file_name": "manual.pdf",
    "page": 25,
    "has_images": true,
    "image_files": "page_025_image_1.png,page_025_image_2.png",
    "source_type": "pdf_ocr"
}
```

## Alternatives Considered

### Alternative 1: Always extract PDFs, ignore markdown
**Rejected:** Wastes processing time, lower quality than processed markdown

### Alternative 2: Ingest both PDF and markdown
**Rejected:** Duplicate content in vector DB, confuses retrieval

### Alternative 3: Delete PDF after markdown creation
**Rejected:** Users may want original PDF for archival purposes

### Alternative 4: Store markdown path in metadata, extract on query
**Rejected:** Too slow, defeats purpose of vector DB

## Edge Cases Handled

### Both Markdown and PDF Exist
```
data/manuals/device/
  ├── manual.pdf                    ← Ignored (original)
  └── manual-English_reference.md   ← Ingested
```
**Result:** Use markdown only, skip PDF

### Multiple Markdown Files
```
data/manuals/device/
  ├── manual1-English_reference.md  ← Ingested
  └── manual2-English_reference.md  ← Ingested
```
**Result:** Ingest all markdown files

### Manually Added PDFs (No Processing)
```
data/manuals/device/
  └── old_manual.pdf  ← Ingested via OCR
```
**Result:** Fall back to PDF extraction

### Empty Markdown File
```
Content: ""
```
**Result:** Skip with warning, continue to next file

## Migration Path

### Existing Manuals (Pre-Change)
- Have PDFs only (no markdown)
- Will continue to work (PDF extraction fallback)

### New Manuals (Post-Change)
- Processed through pipeline
- Create markdown references
- Automatically ingested as markdown

### Rebuilding Vector Store
```bash
# Reset and rebuild with new logic
POST /reset
# Re-upload manuals through processing pipeline
# Markdown files will be ingested correctly
```

## Consequences

### Positive
- ✅ Fixes bug where manuals weren't searchable
- ✅ More efficient ingestion
- ✅ Better RAG quality
- ✅ Backward compatible (legacy PDFs still work)
- ✅ Single source of truth

### Negative
- ⚠️ Assumes processing pipeline always creates markdown
- ⚠️ Manual PDF uploads won't have markdown (falls back to OCR)

### Neutral
- 📊 Vector DB size similar (same content, different source)
- 📊 Retrieval quality unchanged (same embeddings)

## Implementation Status

- [x] Update `_load_manual_files_for_device()` in `backend/ingest.py`
- [x] Implement markdown-first check
- [x] Add PDF extraction fallback
- [x] Add `source_type` to metadata
- [x] Test with both markdown and PDF files
- [x] Verify RAG retrieval works correctly
- [x] Update logging for transparency

## Future Enhancements

### 1. Hybrid Ingestion
Support both markdown (for text) and PDF (for advanced image search):
```python
# Ingest markdown for text content
# Also extract PDF images for vision-based search
```

### 2. Markdown Validation
Verify markdown quality before ingestion:
- Check for minimum content length
- Validate structure
- Ensure translation quality

### 3. Incremental Updates
When markdown is updated, only re-ingest changed sections:
```python
# Diff old vs new markdown
# Update only changed chunks in vector DB
```

### 4. Metadata Enrichment
Extract additional info from markdown:
- Section headings
- Image captions
- Table of contents

## References

- ADR-007: Manual extraction pipeline architecture
- ADR-009: Language section detection
- `backend/ingest.py` - Ingestion implementation
- `backend/manual_processing.py` - Processing pipeline

## Notes

**Why this matters:**
The processing pipeline creates high-quality markdown output. Not using it for ingestion wastes that work and provides worse RAG results.

**Key insight:**
Markdown is not just "another format" - it's the **canonical processed output** of the pipeline. The PDF is the raw input, markdown is the refined output.

