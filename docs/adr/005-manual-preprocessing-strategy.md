# ADR 005: Manual Preprocessing Strategy for RAG System

**Status:** Rejected  
**Date:** 2025-01-07  
**Updated:** 2025-12-08  
**Deciders:** Bruno  
**Technical Story:** Improving retrieval quality by preprocessing manuals before embedding

---

## Context and Problem Statement

The current RAG system embeds raw PDF chunks directly into the vector database. This approach has several quality issues:

1. **Noise Pollution**: Every chunk contains headers/footers (e.g., "SPANISH", page numbers), boilerplate text, and formatting artifacts that pollute embeddings and waste context tokens
2. **Lost Visual Information**: Diagrams, control panel layouts, installation drawings, and tables lose meaning when converted to plain text
3. **Semantic Fragmentation**: References like "See Figure 3" become meaningless without the visual context
4. **Table Degradation**: Structured tables become linear text ("Header1 Header2 Value1 Value2") losing their semantic structure
5. **Language Inconsistency**: Multilingual manuals have mixed content that needs normalization

**Core Question:** How should we preprocess manual PDFs before embedding to maximize retrieval quality while maintaining feasibility?

---

## Decision Drivers

* **Reliability**: Solution must work consistently across different manual formats
* **Speed**: Processing time should be reasonable (minutes to hours, not days)
* **Quality**: Significant improvement in retrieval accuracy and answer quality
* **Maintainability**: Simple enough to debug, modify, and extend
* **Cost**: Must work with local/open-source models (no expensive API dependencies)
* **Scalability**: Should handle multiple manuals without manual intervention

---

## Options Considered

### Option 1: Status Quo (No Preprocessing)

**Description:** Continue embedding raw PDF text chunks without preprocessing.

**Implementation:**
```
PDF → Extract Text → Chunk (800 chars) → Embed → Store
```

**Pros:**
* ✅ Simplest approach - already implemented
* ✅ Fastest processing time (~1 minute per manual)
* ✅ No risk of information loss from preprocessing
* ✅ Works reliably

**Cons:**
* ❌ Noisy embeddings (headers, footers, language indicators)
* ❌ Wastes context tokens on boilerplate text
* ❌ No handling of visual information
* ❌ Tables become incomprehensible
* ❌ References to diagrams are useless

**Evidence:** Current system works but users report confusion when answers reference non-existent figures or include repeated boilerplate.

---

### Option 2: Full Structured Extraction with Vision Models

**Description:** Use vision-capable LLMs to analyze each page and extract comprehensive structured data (operations, troubleshooting, specifications, etc.) into a predefined JSON schema.

**Implementation:**
```
PDF → Render Pages as Images → Vision LLM per page → 
Extract to JSON Schema → Store Structured Data
```

**Attempted Implementation:**
* Tested with `llama3.2-vision:11b` on LG oven manual (96 pages)
* Used `qwen2.5:32b` for text-only extraction

**Pros:**
* ✅ Could capture visual information (diagrams, layouts, icons)
* ✅ Structured data enables advanced queries
* ✅ Complete semantic understanding of manual

**Cons:**
* ❌ **Failed in practice** - vision model hallucinated (generated 188KB of `</div>` tags)
* ❌ Very slow (48-96 minutes for 96 pages with single-image model)
* ❌ Low reliability - models didn't follow instructions (output Spanish despite "English only")
* ❌ Complex schema design required for each appliance type
* ❌ Information loss risk during extraction
* ❌ Difficult to debug extraction errors
* ❌ Single-image limitation made batch processing impossible

**Evidence:**
* Pages 6-7: Corrupted output with ellipses
* Page 8: 188KB file of repeated `</div>` tags (hallucination)
* Page 9: 100 bytes of broken JSON
* Page 10: Process hung and had to be killed
* Text-only model (`qwen2.5:32b`): Ignored instructions, output Spanish summary instead of structured data

**Verdict:** Not viable with current local vision models.

---

### Option 3: LLM-Powered Chunk Cleaning

**Description:** Use a text-based LLM to clean each chunk before embedding, removing noise while preserving semantic content.

**Implementation:**
```
PDF → Extract Text → Chunk → LLM Clean → Embed → Store
                                ↑
                    Remove headers/footers
                    Translate to English
                    Fix fragmented sentences
                    Remove boilerplate
```

**Pros:**
* ✅ Significantly cleaner embeddings
* ✅ Reliable (text models are stable)
* ✅ Reasonable processing time (10-20 min for 96 pages)
* ✅ 20-40% chunk size reduction
* ✅ Same RAG architecture - drop-in improvement
* ✅ Easy to debug and iterate on cleaning prompt
* ✅ Language normalization to consistent English

**Cons:**
* ❌ Doesn't solve visual information problem (diagrams, layouts)
* ❌ Tables still become linear text
* ❌ "See Figure 3" references remain meaningless
* ❌ Processing time increases (10-20min vs 1min)
* ❌ Risk of over-cleaning (removing important context)

**Evidence:** Implemented in `backend/ingest_enhanced.py` but not yet tested on actual manual.

**Verdict:** Partial solution - solves noise but not visual content.

---

### Option 4: Hybrid Approach - Selective Vision Processing

**Description:** Identify pages with significant visual content (diagrams, tables, layouts) and process only those with vision models. Process remaining text-heavy pages with chunk cleaning.

**Implementation:**
```
PDF → Analyze Pages (heuristics: image ratio, table detection)
  ├─> Visual Pages (10-15 per manual) → Vision LLM → Descriptions
  └─> Text Pages (rest) → LLM Clean → Text Chunks
  
Both types stored in same vector DB with type markers
```

**Heuristics to identify visual pages:**
* Page has >30% image content
* Table detection (via borders, grid patterns)
* Keywords: "Figure", "Diagram", "Table", "Control Panel", "Installation"
* Page numbers in ToC that reference diagrams

**Pros:**
* ✅ Captures visual information where it matters
* ✅ Faster than full vision processing (only 10-20% of pages)
* ✅ Falls back to reliable text cleaning for bulk content
* ✅ Can describe control panels, diagrams, installation drawings
* ✅ Balanced approach - quality where needed, speed elsewhere

**Cons:**
* ❌ More complex implementation
* ❌ Heuristics may miss or misidentify visual pages
* ❌ Still dependent on unreliable vision models for some pages
* ❌ Manual review may be needed to identify key visual pages
* ❌ Processing time variable (depends on number of visual pages)

**Verdict:** Promising but complex. Reduces risk by limiting vision model use.

---

### Option 5: Specialized Table Parsing + Chunk Cleaning

**Description:** Use specialized PDF table extraction libraries to detect and parse tables into structured format, convert to natural language. Clean remaining text chunks with LLM.

**Implementation:**
```
PDF → Extract with table detection (tabula-py, unstructured)
  ├─> Tables → Parse to structured data → Convert to prose
  │     "Error code E01 means temperature sensor failure..."
  └─> Regular text → LLM Clean → Text chunks
```

**Pros:**
* ✅ Solves the table problem (major pain point)
* ✅ Reliable - table parsers are mature
* ✅ Still gets chunk cleaning benefits
* ✅ Faster than vision processing
* ✅ Natural language tables are semantic-search friendly

**Cons:**
* ❌ Doesn't solve diagram/image problem
* ❌ Table detection not 100% reliable
* ❌ Complex tables may still be confusing
* ❌ Requires additional dependencies

**Verdict:** Practical improvement that solves one specific problem well.

---

### Option 6: Multimodal RAG with Image Storage

**Description:** Store both cleaned text chunks AND original page images. During retrieval, return both. LLM answers from text, but user can see the original page image.

**Implementation:**
```
PDF → Extract Text + Render Page Images
  ├─> Text → LLM Clean → Embed → Vector DB
  └─> Images → Store with page metadata → Image Store
  
On Retrieval:
  ├─> Semantic search returns text chunks
  └─> Fetch corresponding page image
  └─> Show both to user (LLM uses text, user sees image)
```

**Pros:**
* ✅ No information loss - original visuals preserved
* ✅ User can see diagrams/tables in original context
* ✅ LLM gets clean text for reasoning
* ✅ Flexible - works for any visual content
* ✅ No complex extraction needed

**Cons:**
* ❌ LLM still can't "reason" about visuals
* ❌ Requires UI changes to display images
* ❌ Storage overhead (images per page)
* ❌ User must interpret visual information themselves
* ❌ Doesn't help with automated analysis

**Verdict:** Good for human-in-the-loop workflows, not full automation.

---

## Decision Outcome

**Decision: REJECTED - Pursue specialized OCR model instead**

### Why LLM Chunk Cleaning Was Rejected

**Option 3: LLM-Powered Chunk Cleaning** was implemented but abandoned during testing:

**Problems Encountered:**
* Testing process too slow/unreliable
* Processing time would be 10-20 minutes per manual rebuild
* Added complexity without validated benefit
* Python environment issues made testing difficult

**Key Insight:**
* The root problem isn't just noise - it's **poor text extraction**
* Cleaning bad OCR output doesn't solve tables, diagrams, or layout issues
* Better to extract text properly from the start

### New Direction: Specialized OCR Model

**Decision: Use DeepSeek-OCR for document processing**

**Why This Is Better:**
* Purpose-built for document OCR (not general text cleaning)
* Can preserve tables as markdown (structured)
* Layout-aware extraction
* Handles diagrams/figures better than PyMuPDF
* Solves extraction problem at the source, not as a post-process

**Next Steps:**
1. Test DeepSeek-OCR on sample manual pages
2. Compare output quality to PyMuPDF
3. If promising, create ADR-006 for OCR-based extraction strategy

---

## Consequences

### Positive

* Avoided investing more time in wrong approach
* Identified that extraction quality is the root cause
* Found better solution (DeepSeek-OCR) before full implementation
* Saved 10-20 min per manual rebuild overhead

### Negative

* Time invested in implementing `ingest_enhanced.py` (now unused)
* Need to explore new approach (OCR model)
* Still have noise problem in current system

### Lessons Learned

* Post-processing fixes are inferior to fixing extraction at source
* Always validate assumptions with quick tests before full implementation
* "Clean the data" is less effective than "extract better data"
* Specialized models (OCR) > General models (LLM) for specific tasks

---

## Validation

**Success Metrics for Phase 1:**

1. **Chunk Quality**: Manual review shows <5% information loss
2. **Noise Reduction**: "SPANISH", page numbers absent from >95% of chunks
3. **Retrieval Precision**: Relevant chunks rank higher in search results
4. **Answer Quality**: User queries return cleaner, more focused answers
5. **Processing Time**: <30 minutes per 100-page manual

**Validation Method:**
* Test with 5 diverse queries on LG oven manual
* Compare answers before/after chunk cleaning
* Inspect retrieved chunks for noise content
* Measure processing time

---

## Related Decisions

* ADR-001: Local-first architecture (enables local LLM for chunk cleaning)
* ADR-002: ChromaDB vector storage (where cleaned chunks are stored)
* ADR-004: Manual onboarding workflow (preprocessing happens during onboarding)

---

## Future ADRs to Consider

* ADR-006: Table extraction strategy (if Phase 2 implemented)
* ADR-007: Image storage and retrieval (if Phase 3 multimodal)
* ADR-008: Vision model selection (if Phase 3 hybrid)
* ADR-009: Cloud vs local LLM trade-offs

---

## References

* `backend/ingest_enhanced.py` - Implementation of chunk cleaning
* `test_chunk_cleaning.py` - Testing tool for chunk cleaning
* `CHUNK_CLEANING_APPROACH.md` - Technical documentation
* Session experiments:
  * `extract_manual_ollama.py` - Text-only structured extraction (failed)
  * `extract_manual_vision.py` - Vision-based extraction (failed)
  * Extraction artifacts in `extraction_page_*.txt`

---

## Notes

**Why vision extraction failed:**
* Local vision models (llama3.2-vision:11b) not mature enough
* Single-image limitation makes batch processing impractical  
* Hallucination issues too severe for production use
* May revisit in 6-12 months as models improve

**Key Insight:**
* Perfect is the enemy of good
* 80% solution (chunk cleaning) is achievable now
* 100% solution (full visual reasoning) not feasible locally
* Incremental approach provides value while learning

