# ADR 001: Local-First LLM Architecture Using Ollama

**Status:** Accepted  
**Date:** 2025-01-01 (Retroactive documentation on 2025-01-07)  
**Deciders:** Bruno  
**Technical Story:** Foundation architecture for the home manual assistant

---

## Context and Problem Statement

Building a RAG system for home appliance manuals requires:
* Embedding generation for semantic search
* LLM for question answering
* Processing potentially sensitive home information

Should we use cloud APIs (OpenAI, Anthropic) or local models?

---

## Decision Drivers

* **Privacy**: Home appliance data may contain personal information
* **Cost**: Ongoing API costs vs one-time compute investment
* **Reliability**: Internet dependency and API rate limits
* **Control**: Ability to customize and experiment

---

## Decision

Use **Ollama** for all LLM and embedding needs, running models locally.

**Architecture:**
```
User Query → FastAPI Backend → Ollama (local) → ChromaDB (local) → Response
```

**Models Selected:**
* **Embeddings**: `nomic-embed-text` (274MB)
* **LLM**: `mistral-small:latest` (Mistral 3 8B, ~4.1GB)
* **Translation**: Same `mistral:instruct` model

**Infrastructure:**
* All models run on local hardware
* No external API dependencies
* No data leaves the local network

---

## Alternatives Considered

### Option 1: OpenAI API
**Pros:** Best quality, fast, minimal setup  
**Cons:** Recurring costs, privacy concerns, internet dependency  
**Verdict:** Rejected due to privacy and cost

### Option 2: Anthropic Claude API
**Pros:** Strong reasoning, good for long context  
**Cons:** Expensive, privacy concerns, API dependency  
**Verdict:** Rejected due to privacy and cost

### Option 3: Open-source models (Llama.cpp, Transformers)
**Pros:** Maximum control and flexibility  
**Cons:** Complex setup, manual model management  
**Verdict:** Rejected - Ollama provides better UX with same benefits

### Option 4: Hybrid (local embeddings, cloud LLM)
**Pros:** Lower cost, better privacy for search  
**Cons:** Still sends queries to cloud, partial dependency  
**Verdict:** Rejected - all-or-nothing approach preferred

---

## Consequences

### Positive

* ✅ Complete privacy - all data stays local
* ✅ No recurring API costs
* ✅ Works offline
* ✅ Unlimited queries
* ✅ Fast iteration and experimentation
* ✅ Ollama handles model management elegantly
* ✅ Easy to swap models for testing

### Negative

* ❌ Requires capable local hardware (16GB+ RAM recommended)
* ❌ Model quality lower than GPT-4/Claude
* ❌ Cold start time for model loading
* ❌ Limited to models that fit in local memory
* ❌ No access to cutting-edge cloud models

### Neutral

* Model selection is flexible - can change as better models emerge
* Performance depends on user's hardware
* Requires Ollama installation and setup

---

## Validation

**Success Criteria:**
* Models run on typical consumer hardware (16GB RAM)
* Response time <5 seconds for typical queries
* Quality sufficient for home appliance Q&A

**Results:**
* ✅ Successfully runs on target hardware
* ✅ Response times acceptable
* ✅ Quality sufficient for use case

---

## Related Decisions

* ADR-002: Use of ChromaDB for vector storage
* ADR-003: FastAPI backend choice (Python ecosystem for ML)
* ADR-005: Chunk cleaning with local LLMs

---

## Notes

**Hardware Requirements (Actual):**
* Mistral 8B: ~6GB RAM during inference
* nomic-embed-text: <1GB RAM
* ChromaDB: <500MB for typical manual collection
* Total: ~8GB minimum, 16GB recommended

**Performance Characteristics:**
* Model load time: 2-5 seconds (first query)
* Embedding generation: ~50ms per chunk
* LLM inference: 1-3 seconds per response
* Warm queries: <1 second

**Future Considerations:**
* May reevaluate if local hardware becomes insufficient
* Cloud hybrid possible if privacy requirements change
* Newer, better local models emerging regularly

