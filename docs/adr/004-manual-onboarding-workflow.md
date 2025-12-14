# ADR 004: Three-Step Manual Onboarding Workflow

**Status:** Accepted (Workflow), Superseded (UI Implementation - see ADR-008)  
**Date:** 2025-01-05 (Retroactive documentation on 2025-01-07)  
**Updated:** 2025-12-12 (UI redesigned in ADR-008)  
**Deciders:** Bruno  
**Technical Story:** User-friendly process for adding new manuals to the system

> **Note:** The workflow described here remains valid, but the UI implementation changed in ADR-008 from a side panel to a modal wizard. The core workflow steps and API endpoints remain unchanged.

---

## Context and Problem Statement

Users need to add new appliance manuals to the knowledge base. The process should be:
* Simple enough for non-technical users
* Handle multilingual PDFs (most manuals have multiple languages)
* Extract metadata automatically where possible
* Maintain data quality

How should manual onboarding be designed?

---

## Decision Drivers

* **User experience**: Simple, guided workflow
* **Language handling**: Most manuals are multilingual
* **Metadata quality**: Accurate device information
* **Flexibility**: Handle various manual formats
* **Automation**: Minimize manual data entry

---

## Decision

Implement a **three-step guided workflow** in the frontend:

### Step 1: Prepare Manual
**Choice between two options:**
* **Extract English** - Detect and extract English pages from multilingual PDF
* **Translate to English** - Use LLM to translate entire manual to English

**Implementation:**
* Uses PyMuPDF for page extraction
* Uses Ollama (`mistral:instruct`) for translation
* Stores processed file with token for later steps

### Step 2: Analyze with AI
* LLM reads the manual and extracts metadata automatically
* Fields: device name, brand, model, category, room
* All fields remain editable by user
* Reduces manual data entry

### Step 3: Upload to Knowledge Base
* User reviews and confirms metadata
* System generates unique device ID (slugified name + model)
* Updates `devices.json` catalog
* Moves manual to `data/manuals/<device_id>/`
* Triggers vector DB reindexing for new manual

---

## Workflow Diagram

```
User uploads PDF
    ↓
┌─────────────────────┐
│  Step 1: Prepare    │
│  ○ Extract English  │ → Identify English pages → New PDF with English only
│  ○ Translate        │ → Translate all pages → English PDF
└─────────────────────┘
    ↓ (token stored)
┌─────────────────────┐
│  Step 2: Analyze    │
│  LLM reads manual   │ → Extract metadata → Show editable fields
│  Name: [        ]   │
│  Brand: [       ]   │
│  Model: [       ]   │
└─────────────────────┘
    ↓ (user confirms)
┌─────────────────────┐
│  Step 3: Commit     │
│  - Update catalog   │
│  - Move file        │
│  - Reindex          │
└─────────────────────┘
    ↓
Manual available in knowledge base
```

---

## Alternatives Considered

### Option 1: Manual Entry Only
**Pros:** Simple implementation, full control  
**Cons:** Tedious, error-prone, bad UX  
**Verdict:** Rejected - too much manual work

### Option 2: Automatic Everything
**Pros:** Zero user input  
**Cons:** LLM extraction errors, no validation  
**Verdict:** Rejected - need human oversight

### Option 3: Upload PDF Directly (No Preprocessing)
**Pros:** Fastest workflow  
**Cons:** Multilingual content pollutes embeddings  
**Verdict:** Rejected - see ADR-001 (noise problem)

### Option 4: Two-Step (Skip Language Processing)
**Pros:** Faster  
**Cons:** User must provide English manual  
**Verdict:** Rejected - many manuals are multilingual

---

## Consequences

### Positive

* ✅ Handles common use case (multilingual manuals)
* ✅ Reduces manual data entry with AI extraction
* ✅ User maintains control and can correct errors
* ✅ Clear progress indication
* ✅ Isolated steps make debugging easier
* ✅ Language normalization at ingestion time

### Negative

* ❌ Three steps may feel slow
* ❌ Translation takes 5-10 minutes for large manuals
* ❌ English extraction may miss pages
* ❌ AI metadata extraction not 100% accurate
* ❌ Requires manual review (not fully automated)

### Neutral

* Token-based approach allows resuming interrupted workflow
* Manual language processing only happens once per manual
* Could add "skip to step 3" for English-only manuals

---

## Implementation Details

**API Endpoints:**
```
POST /manuals/extract          # Step 1a: Extract English pages
POST /manuals/translate        # Step 1b: Translate to English
POST /manuals/analyze          # Step 2: AI metadata extraction
POST /manuals/commit           # Step 3: Finalize and index
```

**File Flow:**
```
1. User uploads → data/_uploads/<token>.pdf
2. Process → data/_uploads/<token>_english.pdf
3. Commit → data/manuals/<device_id>/<filename>.pdf
4. Cleanup → Remove _uploads files
```

**Metadata Extraction Prompt Pattern:**
```
"Read this manual and extract: device name, brand, model, 
category, and typical room. Format as JSON."
```

---

## Validation

**Success Criteria:**
* ✅ <3 minutes to onboard a manual (excluding translation)
* ✅ Metadata extraction >80% accurate
* ✅ English extraction catches correct pages
* ✅ Translation maintains technical accuracy

**User Feedback:**
* Step-by-step approach well-received
* Translation time acceptable for one-time cost
* Editable fields important for correction

---

## Related Decisions

* **ADR-008**: Modal wizard UX redesign (UI implementation, 2025-12-12)
* **ADR-007**: Manual extraction pipeline (unified OCR + translation)
* **ADR-005**: Manual preprocessing strategy (chunk cleaning)
* **ADR-001**: Local-first architecture (translation happens locally)
* **ADR-003**: FastAPI + React (enables nice stepper UI)

---

## Future Improvements

**Potential Enhancements:**
* Batch upload multiple manuals
* Save partially completed workflows
* Preview extracted pages before committing
* Smart defaults for common brands (e.g., all "LG" → "LG Electronics")
* OCR support for scanned manuals
* Automatic category detection from product type

---

## Notes

**Language Detection Strategy:**
* PyMuPDF text extraction per page
* Count common English words vs other languages
* Threshold: >60% English words → Keep page
* Works well for typical multilingual manuals (each language in separate pages)

**Translation Considerations:**
* Uses same LLM as chat (`mistral:instruct`)
* Preserves technical terms and model numbers
* ~2-3 minutes per 10 pages (local hardware dependent)
* Alternative: Keep original if manual is English-only

**Device ID Generation:**
* Slugify: "LG Oven WSED7613S" → "lg_oven_wsed7613s"
* Ensures filesystem-safe, URL-safe identifiers
* Collision handling: Append suffix if exists

