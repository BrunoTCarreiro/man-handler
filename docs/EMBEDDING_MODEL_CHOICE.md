# Embedding Model Choice: English-Focused vs Multilingual

**Date:** 2026-01-11  
**Issue:** Why use multilingual `bge-m3` when all content is translated to English?

---

## Current Situation

### Our Translation Pipeline
```
Manual (any language)
  ↓
Language Detection
  ↓
Translation to English
  ↓
Markdown (100% English)
  ↓
Embedding Generation
  ↓
ChromaDB Storage
```

**Key Fact:** By the time content reaches the embedding stage, it's **always in English**.

### Current Configuration
- **Embedding Model:** `bge-m3:latest` (~1.2GB, multilingual)
- **Rationale:** Supports 100+ languages
- **Problem:** We don't need multilingual support post-translation!

---

## Model Comparison

### Option 1: `nomic-embed-text` (English-Focused) ⭐ RECOMMENDED

**Specs:**
- Size: 274MB (~4.4x smaller than bge-m3)
- Languages: English only
- Context: Up to 8,192 tokens
- Dimensions: 768

**Advantages for Our Use Case:**
- ✅ **Smaller & Faster** - 274MB vs 1.2GB
- ✅ **English-optimized** - All semantic capacity focused on English
- ✅ **Better precision** - Fine-tuned for English idioms, phrases, technical terms
- ✅ **Faster embedding generation** - Smaller model = faster inference
- ✅ **Lower memory usage** - Especially beneficial for lower-end hardware
- ✅ **Perfect match** - Our content is 100% English

**Disadvantages:**
- ❌ Can't handle non-English queries (but UI is English-only anyway)
- ❌ Won't help if we skip translation (but we always translate)

### Option 2: `bge-m3:latest` (Multilingual)

**Specs:**
- Size: ~1.2GB
- Languages: 100+ (English, Spanish, French, German, Chinese, etc.)
- Context: Up to 8,192 tokens
- Retrieval: Dense, sparse, and multi-vector

**Advantages:**
- ✅ **Multilingual flexibility** - Could handle queries in any language
- ✅ **State-of-the-art** - Performs well on English benchmarks despite being multilingual
- ✅ **Long documents** - Handles up to 8,192 tokens
- ✅ **Future-proof** - If we ever skip translation for some manuals

**Disadvantages for Our Use Case:**
- ❌ **Larger** - 4.4x bigger than nomic-embed-text
- ❌ **Slower** - More parameters = slower embedding
- ❌ **Overkill** - 99+ languages we don't use
- ❌ **Capacity dilution** - Model capacity spread across many languages

---

## Performance Testing Recommendations

To make an evidence-based decision, test both models:

### Test Setup
1. Use same manual corpus (10 devices, ~50 chunks each)
2. Embed with both models separately
3. Run identical test queries (20-30 questions)
4. Measure:
   - Retrieval precision (are correct chunks retrieved?)
   - Answer quality (is the LLM getting better context?)
   - Embedding time (speed comparison)
   - Memory usage

### Expected Results

**Hypothesis:**
- `nomic-embed-text` will be **faster** and use **less memory**
- Both models should have **similar retrieval quality** (since content is English)
- `nomic-embed-text` may have **slightly better precision** on English technical terms

### How to Test

```bash
# 1. Current setup (bge-m3)
ollama pull bge-m3
# Use app, note performance

# 2. Switch to nomic-embed-text
ollama pull nomic-embed-text
# Update settings via UI: Model Configuration → Embedding Model → nomic-embed-text
# Rebuild vector store (Settings → Reset Database → Re-upload manuals)
# Use app, compare performance

# 3. Compare
# - Query response time
# - Answer relevance
# - Embedding generation speed
```

---

## Recommendation

### For Most Users: `nomic-embed-text` ⭐

**Use `nomic-embed-text` if:**
- ✅ All your manuals are (or will be) translated to English
- ✅ Users query in English only
- ✅ You want faster performance
- ✅ You have limited RAM/CPU
- ✅ You want smaller model downloads

### Use `bge-m3` if:
- You want to skip translation for some manuals (future flexibility)
- You want to support multilingual queries (despite English UI)
- You have ample resources (RAM/CPU)
- You want the absolute latest model

---

## Implementation Path

### Option A: Change Default (Breaking Change)

**Update** `backend/settings.py`:
```python
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "nomic-embed-text")  # Changed from bge-m3
```

**Impact:**
- Existing users must rebuild vector DB
- Requires documentation update

### Option B: Keep Current, Document Alternative (Recommended)

**Keep** `bge-m3` as default, but:
1. Document `nomic-embed-text` as recommended alternative
2. Add note in first-time setup wizard
3. Let users choose based on their priorities
4. Update README with guidance

---

## Decision

**Status:** Pending user testing  
**Recommendation:** Switch default to `nomic-embed-text` for English-only workflows

**Rationale:**
1. Our pipeline produces 100% English content
2. 4.4x size reduction matters for local-first principle
3. Faster is better for user experience
4. No downside given our translation-first approach

**Alternative:** Keep `bge-m3` but document `nomic-embed-text` as preferred option for English-only setups.

---

## Related Documentation

- ADR-001: Local-First LLM Architecture (original model choices)
- ADR-002: ChromaDB for Vector Storage
- backend/settings.py: Model configuration
- backend/config_manager.py: Model selection logic

---

**Next Steps:**
1. Test both models with same corpus
2. Measure performance differences
3. Update default based on results
4. Document final recommendation


