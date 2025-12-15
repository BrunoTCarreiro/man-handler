# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the Home Manual Assistant project.

## What is an ADR?

An ADR is a document that captures an important architectural decision made along with its context and consequences. See [ADR-000](000-use-adr-for-architecture-decisions.md) for our approach.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [000](000-use-adr-for-architecture-decisions.md) | Use Architecture Decision Records | Accepted | 2025-01-07 |
| [001](001-local-first-llm-architecture.md) | Local-First LLM Architecture Using Ollama | Accepted | 2025-01-01 |
| [002](002-use-chromadb-for-vector-storage.md) | Use ChromaDB for Vector Storage | Accepted | 2025-01-02 |
| [003](003-fastapi-react-tech-stack.md) | FastAPI + React Tech Stack | Accepted | 2025-01-03 |
| [004](004-manual-onboarding-workflow.md) | Three-Step Manual Onboarding Workflow | Accepted (Superseded UI) | 2025-01-05 |
| [005](005-manual-preprocessing-strategy.md) | Manual Preprocessing Strategy for RAG System | **Rejected** | 2025-01-07 |
| [006](006-deepseek-ocr-extraction.md) | Use DeepSeek-OCR for Manual Extraction (Prompt 2) | Accepted | 2025-12-08 |
| [007](007-manual-extraction-pipeline.md) | Manual Extraction Pipeline Architecture | Accepted | 2025-12-09 |
| [008](008-modal-wizard-ux-redesign.md) | Modal Wizard UX for Manual Onboarding | Accepted | 2025-12-12 |
| [009](009-language-section-detection.md) | Language Section Detection and Selective Extraction | Accepted | 2025-12-13 |
| [010](010-markdown-first-ingestion.md) | Markdown-First Ingestion Strategy | Accepted | 2025-12-13 |
| [011](011-settings-panel-device-management.md) | Settings Panel and Device Management | Accepted | 2025-12-14 |
| [012](012-device-actions-consolidation.md) | Device Actions Consolidation and View Manual Feature | Accepted | 2025-12-14 |
| [013](013-code-quality-and-configuration.md) | Code Quality Infrastructure and Centralized Configuration | Accepted | 2025-12-15 |

## Decision Status

* **Proposed** - Under consideration
* **Accepted** - Decision made and implemented
* **Deprecated** - No longer applicable
* **Superseded** - Replaced by another ADR

## Contributing

When making significant architectural decisions:
1. Copy the template from an existing ADR
2. Number it sequentially
3. Mark status as "Proposed"
4. Update this README index
5. After acceptance, mark status as "Accepted"

## Key Decisions Timeline

```
2025-01-01 to 2025-01-03: Foundation Architecture
  ├─ ADR-001: Local-first with Ollama
  ├─ ADR-002: ChromaDB for vectors
  └─ ADR-003: FastAPI + React stack

2025-01-05: User Experience (Workflow)
  └─ ADR-004: Three-step onboarding workflow

2025-01-07 to 2025-12-09: Quality Improvements
  ├─ ADR-005: Manual preprocessing (chunk cleaning) - Rejected
  ├─ ADR-006: DeepSeek-OCR extraction (Prompt 2)
  └─ ADR-007: Complete extraction pipeline architecture

2025-12-12 to 2025-12-14: User Experience & Performance
  ├─ ADR-008: Modal wizard UX redesign
  ├─ ADR-009: Language section detection (60-70% time savings)
  ├─ ADR-010: Markdown-first ingestion strategy
  ├─ ADR-011: Settings panel and device management
  └─ ADR-012: Actions dropdown and view manual feature

2025-12-15: Code Quality & Configuration
  └─ ADR-013: Code quality infrastructure and centralized config
```

## Related Documentation

* [UX_REDESIGN_SUMMARY.md](../../UX_REDESIGN_SUMMARY.md) - Technical guide for ADR-008 implementation
* [CHUNK_CLEANING_APPROACH.md](../../CHUNK_CLEANING_APPROACH.md) - Technical guide for ADR-005 implementation
* [README.md](../../README.md) - Project setup and usage
* [tasks.md](../../tasks.md) - Development roadmap

