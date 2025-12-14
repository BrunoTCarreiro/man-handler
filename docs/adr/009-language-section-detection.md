# ADR-009: Language Section Detection and Selective Extraction

**Status:** Accepted  
**Date:** 2025-12-13  
**Decision makers:** Development Team  

## Context

Multilingual product manuals (especially from companies like IKEA, NOOR, etc.) often contain the same content repeated in 10-20 languages. Processing a 178-page manual where only 60 pages are English wastes significant time:

- **Time cost:** ~6 seconds per page OCR = 18 minutes for full manual
- **Resource waste:** Extracting and translating redundant content
- **User experience:** Long waits for processing

Most manuals follow a predictable structure:
```
Pages 1-59:   Swedish
Pages 60-118: English   ← Only this section is needed
Pages 119-178: French
```

## Decision

We will implement a **language pre-scan** before full OCR extraction to:
1. Detect language sections in the PDF
2. Select the best section (prioritizing English)
3. Extract **only** that section

### Architecture

**New Module:** `backend/language_detection.py`

**Functions:**
- `detect_page_language(pdf_path, page_num)` - Fast text extraction + langdetect
- `scan_pdf_languages(pdf_path, sample_interval)` - Sample pages across document
- `group_consecutive_pages(languages, total_pages)` - Group into sections
- `select_best_language_section(sections)` - Pick optimal section
- `detect_and_select_language_section(pdf_path)` - Main entry point

### Sampling Strategy

**Smart Sampling:**
- Always check pages 0-4 individually (language sections often start here)
- Sample every 2nd page after page 5
- For 90-page manual: checks ~47 pages in ~60 seconds

**Why not every page?**
- Text extraction is fast (~1 sec/page) but not instant
- Sampling every 2 pages reliably detects 3-page sections
- Trade-off: 60-second scan vs. 18-minute full extraction

### Selection Priority

**1. English-First Strategy**
- Find ALL English sections
- Select the **longest contiguous English section**
- Ignore all other pages completely

**2. Fallback (No English)**
- Rank languages by translation ease to English
- Select longest section of easiest language
- Translation ranking:
  - Germanic: Dutch (1), German (2), Scandinavian (3-5)
  - Romance: French (6), Spanish (7), Italian (9)
  - Slavic: Polish (11), Czech (12), Russian (13)
  - Other: Turkish (14), Arabic (15), Asian (16-18)

### Integration

**Modified:** `backend/main.py` - `_process_manual_task()`

```python
# Pre-scan for language sections
section_info = detect_and_select_language_section(pdf_path, sample_interval=2)

if section_info:
    language, start_page, end_page = section_info
    # Extract only selected section
    results = extract_pdf_with_ocr(
        pdf_path,
        images_dir,
        page_range=(start_page, end_page)
    )
```

**Modified:** `backend/ocr_extraction.py`

Added `page_range` parameter to `extract_pdf_with_ocr()`:
```python
def extract_pdf_with_ocr(
    pdf_path,
    images_dir,
    page_range: Optional[Tuple[int, int]] = None
)
```

## Example Output

```
[INFO] Scanning PDF for language sections...
  Page 0: de
  Page 1: de  
  Page 2: de
  Page 3: en
  Page 4: en
  Page 5: en
  Page 7: de
  Page 9: fr
  ...
[INFO] Detected 3 section(s):
  - German: pages 1-2 (2 pages)
  - English: pages 3-5 (3 pages)
  - German: pages 6-8 (3 pages)
  - French: pages 9-... (remaining)
[INFO] Found 1 English section(s)
[INFO] Selected longest English section: pages 3-5 (3 pages)
[INFO] Will extract 3 pages instead of entire PDF
[INFO] Starting OCR extraction...
```

## Performance Impact

### Before (Extract Everything)
```
178-page manual:
  OCR: 178 pages × 6 sec = 1,068 seconds (17.8 min)
  Total: 17.8 minutes
```

### After (Smart Selection)
```
178-page manual with 60-page English section:
  Language scan: 47 samples × 1 sec = 47 seconds
  OCR: 60 pages × 6 sec = 360 seconds (6 min)
  Total: 6.8 minutes
  
Savings: 11 minutes (62% faster)
```

### Additional Benefits
- **Better quality:** Native English instead of translated
- **Accurate progress:** Shows actual page counts (3/60 not 3/178)
- **Transparency:** User sees which section was selected

## Alternatives Considered

### Alternative 1: Extract all, filter during ingestion
**Rejected:** Still wastes 18 minutes extracting unnecessary pages

### Alternative 2: User selects language section manually
**Rejected:** Requires user to know PDF structure, adds friction

### Alternative 3: Fixed page ranges per manufacturer
**Rejected:** Not flexible, breaks when manufacturers change layout

### Alternative 4: Extract first N pages only
**Rejected:** Doesn't work if English is in middle or end

## Edge Cases Handled

### Multiple English Sections
```
English: pages 10-20  (11 pages)
German: pages 21-50   (30 pages)
English: pages 51-100 (50 pages)  ← Selected (longest)
Spanish: pages 101+   (remaining)
```
**Result:** Extract pages 51-100 only

### No Clear Sections
```
All pages: Mixed languages or undetectable
```
**Result:** Fall back to extracting all pages

### Very Short Manual (< 10 pages)
**Result:** Scan all pages individually, still select best section

### Language Detection Fails
```
Scanned images with no extractable text
```
**Result:** Fall back to full extraction with OCR

## Consequences

### Positive
- ✅ 60-70% time savings for multilingual manuals
- ✅ Better quality (native English vs translated)
- ✅ Reduced resource usage
- ✅ Improved user experience (faster processing)
- ✅ Works with cancellation (scan can be cancelled too)

### Negative
- ⚠️ 30-60 second scan before OCR starts
- ⚠️ Sampling might miss very short sections (< 2 pages)
- ⚠️ Depends on langdetect accuracy

### Neutral
- 📊 For English-only manuals: adds ~30s scan, saves 0 minutes (net cost)
- 📊 For multilingual manuals: adds ~60s scan, saves 10+ minutes (huge win)

## Implementation Status

- [x] Create `backend/language_detection.py`
- [x] Implement smart sampling (first 5 pages + interval)
- [x] Add page_range support to `extract_pdf_with_ocr()`
- [x] Integrate into processing pipeline
- [x] Add debug logging for transparency
- [x] Test with multilingual IKEA-style manuals
- [x] Handle edge cases (no English, multiple sections, etc.)

## Future Enhancements

### 1. Section Merging (Multiple English Sections)
```
English: pages 10-20
German: pages 21-50
English: pages 51-100
→ Extract pages 10-20 + 51-100 (merge both English sections)
```

### 2. User Override
Allow manual section selection in UI:
```
"Found German, English, Spanish. Which would you like?"
```

### 3. Parallel Extraction
Extract multiple language sections simultaneously for multilingual RAG support

### 4. Improved Language Detection
- Use multiple samples per page
- Confidence scoring
- Better handling of technical content

## References

- ADR-006: DeepSeek-OCR for document extraction
- ADR-007: Manual extraction pipeline architecture
- `backend/language_detection.py` - Implementation
- `LANGUAGE_SECTION_DETECTION.md` - Detailed feature documentation

## Notes

**Why English-first?**
- Primary user base is English-speaking
- No translation needed = better quality
- Most manuals include English section

**Why not use PDF metadata?**
- Most manuals don't have language metadata
- PDF structure doesn't indicate language sections
- Actual content scanning is more reliable

