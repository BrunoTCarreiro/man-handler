# ADR 003: FastAPI + React Tech Stack

**Status:** Accepted  
**Date:** 2025-01-03 (Retroactive documentation on 2025-01-07)  
**Deciders:** Bruno  
**Technical Story:** Selecting web framework and frontend technology

---

## Context and Problem Statement

The home manual assistant needs a backend API and user interface. What technology stack should we use?

---

## Decision Drivers

* **Developer familiarity**: Technologies you're comfortable with
* **Type safety**: Strong typing for maintainability
* **Performance**: Fast enough for real-time chat experience
* **Ecosystem**: Good library support for RAG/LLM integration
* **Development speed**: Rapid iteration and prototyping

---

## Decision

**Backend:** FastAPI (Python)  
**Frontend:** Vite + React + TypeScript

**Architecture:**
```
React App (Port 5173) → FastAPI Backend (Port 8000) → Ollama + ChromaDB
```

---

## Backend Alternatives Considered

### Option 1: Flask
**Pros:** Simple, mature, familiar  
**Cons:** No built-in async, less type safety, older patterns  
**Verdict:** Rejected - FastAPI more modern

### Option 2: Django
**Pros:** Full-featured, batteries included  
**Cons:** Overkill for API-only backend, slower  
**Verdict:** Rejected - too heavy

### Option 3: Express (Node.js)
**Pros:** JavaScript everywhere, npm ecosystem  
**Cons:** Less ideal for ML/AI work, weaker typing  
**Verdict:** Rejected - Python better for LLM integration

---

## Frontend Alternatives Considered

### Option 1: Plain HTML/JS
**Pros:** No build step, simple  
**Cons:** No modern tooling, harder to maintain  
**Verdict:** Rejected - too basic

### Option 2: Vue
**Pros:** Gentler learning curve, good DX  
**Cons:** Smaller ecosystem than React  
**Verdict:** Rejected - React preferred

### Option 3: Svelte
**Pros:** Minimal boilerplate, fast  
**Cons:** Smaller ecosystem, less familiar  
**Verdict:** Rejected - React more established

### Option 4: Next.js
**Pros:** Full-stack React, SSR  
**Cons:** Overkill for SPA, mixing concerns  
**Verdict:** Rejected - prefer separate backend

---

## Consequences

### Positive - Backend (FastAPI)

* ✅ Excellent async support (critical for streaming)
* ✅ Automatic OpenAPI docs
* ✅ Built-in type validation (Pydantic)
* ✅ Fast development with hot reload
* ✅ Great for ML/AI workflows
* ✅ Modern Python (3.10+ features)

### Positive - Frontend (React + Vite)

* ✅ Component reusability
* ✅ TypeScript for type safety
* ✅ Vite: instant hot reload, fast builds
* ✅ Huge ecosystem (libraries, examples)
* ✅ Good for real-time UI updates
* ✅ Dev server with proxy to backend

### Negative

* ❌ Two separate processes to run (backend + frontend)
* ❌ CORS configuration needed
* ❌ More complex deployment than monolith
* ❌ Build step required for frontend

---

## Implementation Details

**Backend Structure:**
```
backend/
├── main.py              # FastAPI app + routes
├── rag_pipeline.py      # RAG logic
├── ingest.py           # Vector DB building
├── device_catalog.py   # Device management
└── settings.py         # Configuration
```

**Frontend Structure:**
```
frontend/
├── src/
│   ├── App.tsx         # Main component
│   ├── api/client.ts   # Backend API calls
│   └── styles.css
├── vite.config.ts      # Build config + proxy
└── package.json
```

**Development Workflow:**
```bash
# Terminal 1: Backend
python -m uvicorn backend.main:app --reload

# Terminal 2: Frontend  
cd frontend && npm run dev
```

---

## Validation

**Success Criteria:**
* ✅ Development server runs smoothly
* ✅ Hot reload works for both frontend and backend
* ✅ Type safety catches errors early
* ✅ API documentation auto-generated
* ✅ Build process is fast

---

## Related Decisions

* ADR-001: Local-first architecture (affects API design)
* ADR-004: Manual onboarding workflow (major UI feature)

---

## Notes

**Why FastAPI:**
* Async crucial for streaming LLM responses (future feature)
* Pydantic models match nicely with TypeScript interfaces
* `/docs` endpoint invaluable for testing

**Why Vite over Create-React-App:**
* CRA deprecated/unmaintained
* Vite much faster (ESBuild vs Webpack)
* Simpler configuration

**Port Selection:**
* 8000: FastAPI (Python web framework convention)
* 5173: Vite default (avoids conflicts)

**Type Sharing:**
* Currently duplicated types between frontend/backend
* Future: Could generate TypeScript from Pydantic models

