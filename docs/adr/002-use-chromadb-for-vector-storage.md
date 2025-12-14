# ADR 002: Use ChromaDB for Vector Storage

**Status:** Accepted  
**Date:** 2025-01-02 (Retroactive documentation on 2025-01-07)  
**Deciders:** Bruno  
**Technical Story:** Selecting vector database for semantic search

---

## Context and Problem Statement

The RAG system needs a vector database to store and retrieve embedded manual chunks. Which vector database should we use?

---

## Decision Drivers

* **Simplicity**: Easy to setup and integrate
* **Local-first**: Must work entirely locally (see ADR-002)
* **Python integration**: Good LangChain support
* **Performance**: Fast enough for small-to-medium collections
* **Storage**: Persistent storage without complex configuration

---

## Decision

Use **ChromaDB** as the vector database.

**Configuration:**
* Persistent storage in `data/vectordb/`
* Integrated via LangChain's Chroma wrapper
* Uses default HNSW indexing

---

## Alternatives Considered

### Option 1: FAISS
**Pros:** Very fast, Facebook-backed, mature  
**Cons:** Requires manual persistence, more complex setup  
**Verdict:** Rejected - too much manual management

### Option 2: Pinecone
**Pros:** Excellent performance, managed service  
**Cons:** Cloud-only, recurring costs, against local-first principle  
**Verdict:** Rejected - not local

### Option 3: Weaviate
**Pros:** Feature-rich, good for production  
**Cons:** Requires Docker/server setup, overkill for use case  
**Verdict:** Rejected - too complex

### Option 4: Qdrant
**Pros:** Modern, fast, good API  
**Cons:** Requires separate server process  
**Verdict:** Rejected - prefer embedded solution

### Option 5: Milvus
**Pros:** Production-grade, scalable  
**Cons:** Heavy infrastructure, overkill for home use  
**Verdict:** Rejected - too complex

---

## Consequences

### Positive

* ✅ Zero-config embedded database
* ✅ Automatic persistence
* ✅ Excellent LangChain integration
* ✅ Good performance for <100k vectors
* ✅ Simple file-based storage
* ✅ Easy to backup (just copy folder)
* ✅ No separate server process

### Negative

* ❌ Not optimal for very large collections (>1M vectors)
* ❌ Limited advanced features vs production DBs
* ❌ Single-process access (no concurrent writes)

### Neutral

* Sufficient for home manual use case (~1-10k vectors)
* Can migrate to different DB if needs change

---

## Validation

**Current Usage:**
* ~5 devices × ~100 pages × 3-5 chunks = ~2,500 vectors
* Query time: <100ms
* Storage: ~10MB (vectors + metadata)

**Success Criteria:**
* ✅ Handles expected data volume
* ✅ Query latency acceptable
* ✅ Storage size reasonable

---

## Related Decisions

* ADR-001: Local-first architecture
* ADR-001: Choice of embedding model (affects vector dimensions)

---

## Notes

**ChromaDB Storage Structure:**
```
data/vectordb/
├── chroma.sqlite3          # Metadata
└── <collection-id>/
    ├── data_level0.bin     # HNSW index
    ├── header.bin
    ├── length.bin
    └── link_lists.bin
```

**Migration Path:**
* If scale requires: ChromaDB → Qdrant (similar API)
* If cloud needed: ChromaDB → Pinecone (LangChain supports both)
* Current setup supports 100+ manuals comfortably

