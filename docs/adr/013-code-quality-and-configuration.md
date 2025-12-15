# ADR-013: Code Quality Infrastructure and Centralized Configuration

**Status:** Accepted  
**Date:** 2025-12-15  
**Decision makers:** Development Team  

## Context

As the Home Manual Assistant project grew, several code quality and configuration issues emerged:

1. **No dependency version pinning** - `requirements.txt` had no version constraints, risking breaking changes
2. **Memory leak** - Processing status dictionaries were never cleaned up
3. **Deprecated API usage** - ChromaDB `persist()` calls were deprecated in v0.4+
4. **No linting** - Both frontend and backend lacked linting/formatting tools
5. **Double retrieval** - RAG pipeline fetched documents twice (once for context, once for sources)
6. **No error boundary** - React crashes took down the entire app
7. **Hardcoded configuration** - CORS origins and other settings were hardcoded
8. **Inconsistent logging** - Mixed `print()` statements with no log levels

## Decision

We will implement comprehensive code quality infrastructure and centralized configuration management.

### Changes Overview

| Category | Implementation |
|----------|----------------|
| Dependency Management | Pin all Python dependencies with version ranges |
| Memory Management | TTL-based cleanup for processing status |
| API Compatibility | Remove deprecated ChromaDB calls |
| Frontend Linting | ESLint + Prettier with React/TypeScript plugins |
| Backend Linting | Ruff configuration via pyproject.toml |
| RAG Optimization | Single retrieval for context and sources |
| Error Handling | React Error Boundary component |
| Configuration | Environment variables with validation |
| Logging | Python logging module with configurable levels |

## Implementation

### 1. Dependency Version Pinning

**File:** `backend/requirements.txt`

```
fastapi>=0.104.0,<1.0.0
uvicorn[standard]>=0.24.0,<1.0.0
langchain>=0.1.0,<0.3.0
langchain-community>=0.0.10,<0.3.0
langchain-ollama>=0.1.0,<0.3.0
chromadb>=0.4.0,<0.6.0
pydantic>=2.0.0,<3.0.0
python-multipart>=0.0.6,<1.0.0
pypdf>=3.0.0,<5.0.0
langdetect>=1.0.9,<2.0.0
reportlab>=4.0.0,<5.0.0
```

**Strategy:** Use `>=min,<max` ranges to allow patch updates while preventing major version breaks.

### 2. Processing Status TTL Cleanup

**File:** `backend/main.py`

```python
STATUS_TTL_SECONDS = 3600  # 1 hour

def cleanup_expired_statuses() -> None:
    """Remove processing status entries older than TTL."""
    current_time = time.time()
    with status_lock:
        expired_tokens = [
            token for token, status in processing_status.items()
            if current_time - status.get("created_at", 0) > STATUS_TTL_SECONDS
        ]
        for token in expired_tokens:
            del processing_status[token]
            if token in cancellation_flags:
                del cancellation_flags[token]
```

- Each status entry gets a `created_at` timestamp
- Cleanup runs on each status poll request
- Expired entries (>1 hour) are automatically removed

### 3. ChromaDB API Update

**File:** `backend/ingest.py`

Removed deprecated `store.persist()` calls. ChromaDB v0.4+ auto-persists to disk.

### 4. Frontend Linting (ESLint + Prettier)

**Files:**
- `frontend/.eslintrc.cjs` - ESLint configuration
- `frontend/.prettierrc` - Prettier configuration
- `frontend/package.json` - New dev dependencies and scripts

**ESLint Plugins:**
- `@typescript-eslint` - TypeScript support
- `eslint-plugin-react` - React rules
- `eslint-plugin-react-hooks` - Hooks rules
- `eslint-plugin-react-refresh` - Hot reload safety
- `eslint-config-prettier` - Prettier compatibility

**Scripts:**
```json
{
  "lint": "eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
  "lint:fix": "eslint src --ext ts,tsx --fix",
  "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
  "format:check": "prettier --check \"src/**/*.{ts,tsx,css}\""
}
```

### 5. Backend Linting (Ruff)

**File:** `backend/pyproject.toml`

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
```

Run with: `ruff check backend/` and `ruff format backend/`

### 6. RAG Pipeline Optimization

**File:** `backend/rag_pipeline.py`

**Before (2 retrievals):**
```python
answer = chain.invoke({"question": question})  # retrieves once
source_docs = retriever.invoke(question)        # retrieves again
```

**After (1 retrieval):**
```python
# Retrieve once, use for both
source_docs = retriever.invoke(question)
context = _format_docs(source_docs)

chain = prompt | llm | StrOutputParser()
answer = chain.invoke({"context": context, "question": question})
sources = _build_sources_from_docs(source_docs)
```

**Benefits:**
- 50% fewer embedding API calls
- Guaranteed consistency between context and cited sources
- Faster response time

### 7. React Error Boundary

**Files:**
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/components/ErrorBoundary.css`

```tsx
export class ErrorBoundary extends Component<Props, State> {
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <button onClick={this.handleReset}>Try Again</button>
          <button onClick={() => window.location.reload()}>Reload Page</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

Wraps `<App />` in `main.tsx` to catch rendering errors gracefully.

### 8. Centralized Configuration

#### Backend (`backend/settings.py`)

All configuration now supports environment variables:

```python
# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# CORS
CORS_ORIGINS = [origin.strip() for origin in 
    os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")]

# Models
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "bge-m3")
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "mistral:instruct")

# Retrieval
TOP_K = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
```

#### Frontend (`frontend/src/config.ts`)

```typescript
function validateUrl(url: string, name: string): string {
  try {
    new URL(url);
    return url;
  } catch {
    console.warn(`[Config] Invalid URL for ${name}: "${url}". Using default.`);
    return "http://localhost:8000";
  }
}

export const config = {
  apiBaseUrl: validateUrl(
    getEnvVar("VITE_API_BASE_URL", "http://localhost:8000"),
    "VITE_API_BASE_URL"
  ),
} as const;
```

### 9. Structured Logging

Replaced all `print()` statements with Python `logging`:

```python
import logging

logger = logging.getLogger("backend.module_name")

# Instead of: print(f"[INFO] Processing...")
logger.info("Processing...")

# Instead of: print(f"[WARN] Failed: {e}")
logger.warning("Failed: %s", e)

# Instead of: print(f"[OK] Done")
logger.info("Done")
```

**Log Levels:**
- `DEBUG` - Verbose output (page-by-page progress)
- `INFO` - Standard operations (file processed, device added)
- `WARNING` - Non-fatal issues (translation failed, falling back)
- `ERROR` - Failures (PDF won't open, API error)

**Configuration:**
```bash
LOG_LEVEL=DEBUG  # See all logs
LOG_LEVEL=INFO   # Normal operation (default)
LOG_LEVEL=WARNING  # Only problems
```

## Files Changed

| File | Changes |
|------|---------|
| `backend/requirements.txt` | Version pinning |
| `backend/main.py` | TTL cleanup, logging |
| `backend/ingest.py` | Remove persist(), logging |
| `backend/rag_pipeline.py` | Single retrieval |
| `backend/settings.py` | Env vars, logging config |
| `backend/manual_processing.py` | Logging |
| `backend/language_detection.py` | Logging |
| `backend/ocr_extraction.py` | Logging |
| `backend/translation.py` | Logging |
| `backend/ingest_enhanced.py` | Logging, remove persist() |
| `backend/pyproject.toml` | Ruff config (new) |
| `backend/env.example` | Env template (new) |
| `frontend/package.json` | Lint scripts, dev deps |
| `frontend/.eslintrc.cjs` | ESLint config (new) |
| `frontend/.prettierrc` | Prettier config (new) |
| `frontend/src/config.ts` | Centralized config (new) |
| `frontend/src/api/client.ts` | Use config module |
| `frontend/src/main.tsx` | Error boundary wrapper |
| `frontend/src/components/ErrorBoundary.tsx` | Error boundary (new) |
| `frontend/src/components/ErrorBoundary.css` | Styling (new) |
| `README.md` | Environment variables docs |

## Consequences

### Positive

- ✅ **Stability** - Version pinning prevents unexpected breaks
- ✅ **No memory leaks** - Status entries auto-expire after 1 hour
- ✅ **Future-proof** - No deprecated API warnings
- ✅ **Code quality** - Linting catches bugs before runtime
- ✅ **Consistency** - Prettier ensures uniform formatting
- ✅ **Performance** - Single retrieval = faster responses
- ✅ **Reliability** - Error boundary prevents full crashes
- ✅ **Flexibility** - All config via environment variables
- ✅ **Debuggability** - Structured logging with levels
- ✅ **Observability** - Timestamps and module names in logs

### Negative

- ⚠️ **Initial setup** - Developers need to run `npm install` again
- ⚠️ **Stricter linting** - May require fixing existing code
- ⚠️ **Learning curve** - New tools to learn (Ruff, ESLint config)

### Neutral

- 📊 ~500 lines of configuration added
- 📊 ~100 print statements converted to logging
- 📊 No functional changes to user-facing features

## Migration Notes

### For Developers

1. **Backend:**
   ```bash
   pip install -r backend/requirements.txt  # Updated deps
   pip install ruff  # Optional: for linting
   ```

2. **Frontend:**
   ```bash
   cd frontend && npm install  # New dev dependencies
   npm run lint  # Check for issues
   npm run lint:fix  # Auto-fix issues
   ```

3. **Environment:**
   ```bash
   cp backend/env.example backend/.env  # Create local config
   # Edit .env as needed
   ```

### For Users

No changes required. All defaults match previous behavior.

## Future Enhancements

1. **CI/CD Integration** - Add lint checks to GitHub Actions
2. **Pre-commit Hooks** - Auto-lint on commit
3. **Test Coverage** - Add pytest with coverage reporting
4. **Type Checking** - Add mypy for Python type validation
5. **Log Aggregation** - Structured JSON logs for production

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [ESLint TypeScript](https://typescript-eslint.io/)
- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [ChromaDB Migration Guide](https://docs.trychroma.com/migration)

