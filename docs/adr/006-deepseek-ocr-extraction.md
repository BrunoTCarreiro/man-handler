# ADR-006: Use DeepSeek-OCR for Manual Text and Image Extraction

**Status:** Accepted  
**Date:** 2025-12-08  
**Decision makers:** Development Team

## Context

PyMuPDF text extraction (`page.get_text()`) has significant limitations for appliance manuals:

1. **No table structure** - Extracts table data as unstructured text, losing row/column relationships
2. **No diagram extraction** - Cannot extract images, diagrams, or illustrations
3. **Layout issues** - Poor handling of multi-column layouts, headers, footers
4. **No semantic understanding** - Cannot differentiate between body text, titles, captions, etc.

This results in poor RAG quality because:
- Users ask about diagrams/illustrations ("show me the control panel layout") but we can't retrieve them
- Table data is scrambled and hard to query
- Context is lost when text extraction ignores visual elements

We need a solution that can:
- Extract structured text (markdown with tables, headings, etc.)
- Identify and extract images/diagrams with their locations
- Maintain document layout and semantics
- Work locally (no API costs, no data leaving the machine)

## Decision

We will use **DeepSeek-OCR** (via Ollama) for text and image extraction from PDF manuals.

### Implementation approach:

**UPDATED 2025-12-09**: After testing all three prompts, **Prompt 2** was chosen as the single best option.

1. **Page rendering**: Extract each PDF page as a PNG image using PyMuPDF at 1x resolution
   - Ollama resizes all images to 1000×1000, so higher resolution just causes coordinate misalignment

2. **OCR with Prompt 2** (Single call - most efficient):
   ```
   "<|grounding|>Convert the document to markdown."
   ```
   - **Returns both text AND coordinates in one call**
   - Best text quality (more complete than Prompt 1)
   - Includes grounding tags embedded: `<|ref|>TYPE<|/ref|><|det|>[[x1, y1, x2, y2]]<|/det|>`
   - Element types: image, figure, table, text, title, header
   - Coordinates are in 1000×1000 space (Ollama's resize target)
   - **Key benefit**: ~2x faster than calling Prompt 1 + Prompt 3 separately

3. **Parse grounding tags**:
   - Extract coordinate information from embedded tags
   - Filter for `image` and `figure` elements only

4. **Coordinate transformation**:
   - Ollama resizes images to 1000×1000 regardless of aspect ratio
   - Transform model coordinates back to original image: `original_coord = model_coord × (original_size / 1000)`
   - Extract image regions using transformed coordinates

5. **Clean text**:
   - Strip grounding tags from markdown text before storage
   - Results in clean, readable markdown without coordinate artifacts

6. **Image extraction**:
   - Extract each detected image/figure as a separate PNG file
   - Save with naming: `page_XXX_image_N.png`

### Coordinate System Details

**Critical discovery**: Ollama resizes ALL input images to exactly **1000×1000 pixels** before passing to DeepSeek-OCR, regardless of original aspect ratio. This means:

- A 827×1169 page becomes 1000×1000 (stretched)
- Model outputs coordinates in 1000×1000 space
- To get original coordinates: multiply by `(original_width/1000, original_height/1000)`

```python
def calculate_ollama_scale(original_width: int, original_height: int) -> tuple[float, float]:
    """Calculate scale factors to transform model coords back to original image."""
    scale_x = original_width / 1000
    scale_y = original_height / 1000
    return scale_x, scale_y
```

## Alternatives considered

1. **Continue with PyMuPDF** - REJECTED: Cannot extract images, poor table handling
2. **PDF.js or similar** - REJECTED: Still no semantic understanding or image extraction
3. **Cloud OCR APIs** (Google Vision, AWS Textract) - REJECTED: Costs money, requires internet, data leaves machine
4. **Tesseract OCR** - REJECTED: No document understanding, just raw OCR without structure
5. **LLM chunk cleaning** (ADR-005) - REJECTED: Post-processing doesn't fix missing images/tables

## Consequences

### Positive

- ✅ **Structured text**: Markdown with proper tables, headings, lists
- ✅ **Image extraction**: Can retrieve diagrams, control panels, installation guides
- ✅ **Better RAG quality**: Structured data + images = more accurate answers
- ✅ **Local-first**: Runs on Ollama, no API costs, data stays local
- ✅ **Layout awareness**: Model understands document structure

### Negative

- ⚠️ **Processing time**: Vision model inference is slower than PyMuPDF text extraction (~2-3s per page vs <1s)
- ⚠️ **Disk space**: Storing extracted images increases storage requirements
- ⚠️ **Complexity**: More moving parts (image rendering, coordinate transformation, grounding parsing)
- ⚠️ **Coordinate accuracy**: Depends on Ollama's 1000×1000 resize maintaining quality

### Neutral

- 📊 **Image quality**: 1x resolution sufficient for text extraction, but diagrams may need higher res
- 📊 **Prompt tuning**: May need to refine prompts for optimal results per manual type

## Implementation notes

### Key files

- `test_deepseek_ocr.py`: Test script demonstrating the full pipeline
- `backend/manual_processing.py`: Will implement this approach for production ingestion

### Processing pipeline

```
PDF → PyMuPDF → PNG (1x) → Ollama/DeepSeek-OCR → {
    Prompt 1: Markdown text
    Prompt 3: Element coordinates (grounding)
} → Transform coordinates → Extract images → Integrate → ChromaDB
```

### Storage in ChromaDB

Each page chunk will include:
- **Text**: Markdown formatted text
- **Metadata**: 
  - `page_number`: int
  - `manual_id`: str
  - `device_id`: str
  - `has_images`: bool
  - `image_refs`: list of image filenames
- **Images**: Stored separately with references in markdown

## Testing

Testing done via `test_deepseek_ocr.py` on pages 10, 25, 50 of LG oven manual:
- ✅ Text extraction produces clean markdown
- ✅ Coordinate transformation works accurately
- ✅ Image extraction successful
- ✅ Debug visualizations show correct bounding boxes

## Future considerations

1. **Image-description linking**: Enhance prompts to capture semantic relationships between diagrams and their legends/captions (see discussion)
2. **Table extraction**: May need dedicated prompt for complex tables
3. **Multi-language**: Test on non-English manuals
4. **Batch processing**: Optimize for processing entire manual directories
5. **Resolution tuning**: May need higher resolution for detailed diagrams

## References

- [DeepSeek-OCR on Ollama](https://ollama.com/library/deepseek-ocr)
- [Test script](../../test_deepseek_ocr.py)
- [ADR-005: LLM Chunk Cleaning](./005-manual-preprocessing-strategy.md) (Rejected)
