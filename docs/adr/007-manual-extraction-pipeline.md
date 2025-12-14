# ADR-007: Manual Extraction Pipeline Architecture

**Status:** Accepted  
**Date:** 2025-12-09  
**Decision makers:** Development Team  

## Context

After implementing DeepSeek-OCR extraction (ADR-006), we need to define the complete pipeline from PDF to usable text. The system needs to support:

1. **Quality validation** - Human-in-the-loop checkpoints during development
2. **Multiple outputs** - Different formats for different purposes (debugging, user reference, RAG ingestion)
3. **Translation** - Convert non-English manuals to English
4. **Image handling** - Extract and reference diagrams inline
5. **Standalone extraction** - Make the extraction tool independent of the RAG application

## Decision

We will implement a **multi-stage extraction pipeline** with three distinct output formats:

### 1. Debug Markdown (Optional, dev-time only)

**File:** `{manual_name}_extraction_debug.md`  
**Purpose:** Quality validation during development  
**Content:**
- Raw OCR output in original language
- Page numbers included (## Page N)
- Image file references listed at page end
- Grounding tags removed

**Generation:** Via `--debug` flag on extraction tool  
**Use case:** Verify OCR quality, check for extraction errors

### 2. User Reference Markdown (Always generated)

**File:** `{manual_name}_reference.md`  
**Purpose:** Human-readable fallback document  
**Content:**
- Translated to English
- No page numbers (continuous document)
- Images rendered inline at correct position
- Clean, publication-ready formatting

**Example:**
```markdown
## Operating Instructions

The oven features three cooking modes...

![Figure 1: Control Panel Layout](images/page_025_image_1.png)

To select a mode, press the...
```

**Use case:** 
- User fallback if RAG retrieval fails
- Quick reference document
- Printable manual

### 3. ChromaDB Ingestion (Database storage)

**Output:** Vector embeddings in ChromaDB  
**Process:**
- Reads the markdown reference file (ADR-010: Markdown-first ingestion)
- Content is already translated to English
- Split into chunks (~800 chars)
- Embedded with `bge-m3`
- Metadata includes: device ID, device metadata, source type

**Use case:** RAG retrieval for chat interface

## Architecture Components

### Module: `backend/translation.py` (NEW)

**Purpose:** Reusable translation module  
**Functions:**
- `translate_text(text: str, target_lang: str = "English", model: str | None = None) -> str`
- `translate_in_chunks(text: str, target_lang: str = "English", chunk_size: int = 4000, model: str | None = None) -> str`
- `detect_language(text: str, model: str | None = None) -> str`
- `clean_translated_markdown(text: str, model: str | None = None) -> str` (second-pass cleanup)

**Behavior:**
- Uses local Ollama models (default from `settings.TRANSLATION_MODEL_NAME`)
- Prompt explicitly requires:
  - Translate **all** content (including table headers/cells)
  - Preserve markdown
  - No explanations or commentary
- Post-processing removes leaked prompts, code fences, and LLM commentary
- Second pass (`clean_translated_markdown`) re-translates obviously Spanish-heavy paragraphs and strips remaining artifacts

**Why separate module:** May be needed elsewhere (onboarding, user queries, etc.)

### Tool: `extract_manual.py` (NEW - Renamed from `test_ocr_ingestion.py`)

**Purpose:** Standalone extraction tool  
**Usage:**
```bash
python extract_manual.py <pdf_path> [--debug] [--output-dir <dir>]
```

**Outputs:**
- User reference MD (always)
- Debug MD (if `--debug` flag)
- Images directory with extracted figures

**Why standalone:** 
- Useful tool independent of RAG application
- Can be used for batch processing
- Potential future: package as separate utility

### Module: `backend/ocr_extraction.py` (Existing, updated)

**Purpose:** Core OCR functionality  
**Updates (2025-12-10):**
- Render pages at 2x resolution before OCR to produce sharper cropped figures
- Keep coordinate alignment correct by mapping DeepSeek-OCR's 1000x1000 space back to the higher-resolution image

### Module: `backend/ingest.py` (Existing - Updated)

**Purpose:** ChromaDB ingestion  
**Updates needed:**
- Use OCR extraction (already done)
- Add translation step before chunking
- Store image metadata in document metadata

## Image Description Strategy

**Current implementation:** Generic labels
- "Figure 1", "Figure 2", "Diagram 1", etc.
- Based on order of appearance

**Future enhancement (TODO):**
- Use vision model to describe images
- More meaningful labels: "Oven Control Panel Diagram", "Temperature Settings Chart"
- See: ADR-008 (future) for vision-based descriptions

## Translation & Reference Generation

**Current approach (unified OCR flow via `/manuals/process`):**
- **Language pre-scan** (ADR-009): Detect language sections and select best one (typically English)
- Run OCR (`extract_pdf_with_ocr`) on the selected section only (per-page text + images)
- Detect language from extracted text (or use pre-scan result)
- Generate the reference markdown with `generate_reference_md`:
  - If detected language is non-English, translate during reference generation
  - Inline images with correct relative paths
- The older page-by-page translation and second-pass cleaning remain available in `backend/translation.py`, but the frontend now uses the OCR-based pipeline end-to-end

**Trade-offs:**
- ✅ Single API call covers OCR + detect + translate + reference generation.
- ✅ Image paths correct relative to output MD.
- ⚠️ Translation still depends on local LLM quality and adds time.
- ⚠️ Full OCR+translate on large manuals is slow.

**Future consideration:** Allow per-request model override for translation during `generate_reference_md`, and/or fallback to chunked translation for very large docs.

## File Organization

```
data/manuals/<device_id>/
  ├── manual.pdf                       # Original PDF
  ├── images/                          # Extracted images
  │   ├── page_001_image_1.png
  │   ├── page_025_image_1.png
  │   └── ...
  └── reference.md                     # User reference document

Project root (dev-time only):
  └── <manual>_extraction_debug.md     # Debug output (gitignored)
```

## Workflow

### Development/Testing:
```bash
# 1. Extract with debug output
python extract_manual.py data/manuals/lg_oven/manual.pdf --debug

# 2. Review debug MD for quality

# 3. If good, rebuild vector store
python -m backend.ingest
```

### Production:
```bash
# Just rebuild vector store (includes OCR + translation)
python -m backend.ingest
```

## Alternatives Considered

### Alternative 1: Single output format
**Rejected:** Different use cases need different formats. Debug output clutters user docs.

### Alternative 2: Translate during retrieval
**Rejected:** Too slow. Better to translate once during ingestion.

### Alternative 3: Keep extraction in test script
**Rejected:** Extraction is useful standalone. Making it a proper tool enables future reuse.

### Alternative 4: Immediate vision-based image descriptions
**Rejected:** High complexity, low immediate value. Start simple, enhance later.

## Consequences

### Positive

- ✅ Clear separation of concerns (extraction, translation, ingestion)
- ✅ Human validation checkpoints during development
- ✅ Reusable components (translation module)
- ✅ Standalone extraction tool has value beyond RAG
- ✅ User reference document provides fallback UX

### Negative

- ⚠️ More files to manage
- ⚠️ Translation adds processing time (~30-60s per manual, more with second pass)
- ⚠️ Generic image labels less helpful than descriptions

### Neutral

- 📊 Translation quality depends on mistral:instruct capability
- 📊 Manual storage size increases with reference MD + images

## Implementation Tasks

- [x] Create `backend/translation.py`
- [x] Rename `test_ocr_ingestion.py` to `extract_manual.py`
- [x] Add `--debug` flag for debug MD generation
- [x] Generate user reference MD with inline images
- [x] Update ingestion to use OCR-extracted/translated reference
- [x] Test full pipeline on LG oven manual (including debug/reference outputs)
- [x] Add second-pass cleanup for translated markdown (`clean_translated_markdown`) — legacy path
- [x] Add CLI flags to `extract_manual.py`:
  - `--skip-index-pages` to drop front-matter / TOC pages from reference MD
  - `--translation-model` to choose Ollama model per run
- [x] Document unified “Process manual” flow in README

## Future Work (TODOs)

- [ ] **Vision-based image descriptions** (ADR-008)
  - Use vision model to describe each extracted image
  - Generate meaningful labels automatically
  - Requires: Better vision model or cloud API

- [ ] **Make extraction tool more configurable**
  - Support different output formats
  - Add batch processing for multiple PDFs
  - Configuration file for model/prompt choices

- [ ] **Package extraction as standalone utility**
  - Could be useful outside this project
  - Separate repo: `pdf-to-markdown-ocr`

## References

- ADR-006: DeepSeek-OCR for document extraction
- ADR-009: Language section detection and selective extraction
- ADR-010: Markdown-first ingestion strategy
- `backend/ocr_extraction.py` - Core OCR implementation
- `backend/translation.py` - Translation module (new)
- `extract_manual.py` - Standalone extraction tool (new)

## Notes

**Why three formats?**
- Debug MD: Developer needs quality validation
- Reference MD: User needs readable fallback
- ChromaDB: RAG system needs searchable chunks

Each serves a distinct purpose and audience.

**Why translation at extraction, not retrieval?**
- Translate once, query many times (performance)
- Embeddings work better with consistent language
- User queries typically in English already

