# ADR-014: First-Time Setup Wizard and Configuration Management

**Status:** Accepted  
**Date:** 2026-01-06  
**Decision makers:** Development Team  
**Technical Story:** Guided first-run experience and dynamic model configuration

---

## Context and Problem Statement

The application previously assumed Ollama was running with specific models (`mistral:instruct`, `bge-m3`) already pulled. This created several issues:

1. **Poor first-run experience** - App would fail silently if models weren't available
2. **No model flexibility** - Users couldn't switch models without editing code
3. **Hidden dependencies** - No clear indication of required setup
4. **Configuration sprawl** - Settings scattered across environment variables and code
5. **No validation** - App couldn't verify Ollama was running or models were available

**Question:** How can we provide a guided setup experience while allowing model/configuration changes post-setup?

---

## Decision Drivers

* **User experience** - First-time users shouldn't face cryptic errors
* **Flexibility** - Users should be able to switch models without code changes
* **Validation** - System should verify models work before accepting configuration
* **Persistence** - Configuration should survive app restarts
* **Separation of concerns** - Setup vs runtime configuration
* **Discoverability** - Settings should be accessible and obvious

---

## Decision

We will implement a **two-phase configuration system**:

### Phase 1: First-Time Setup Wizard

**When:** App first run (no `data/config.json` exists)

**Purpose:** Guide user through initial configuration

**Steps:**
1. **Ollama Connection Check** - Verify Ollama is running
2. **Model Selection** - Choose LLM and embedding models from available options
3. **Model Testing** - Validate models work before completion
4. **Complete Setup** - Persist configuration and unlock main app

**Blocking:** Main app is inaccessible until setup completes (intentional)

### Phase 2: Settings Panel Configuration

**When:** After setup, accessible from sidebar

**Purpose:** Allow model switching and parameter tuning

**Features:**
- View current model configuration
- Switch LLM, embedding, and translation models
- Test models before switching
- Advanced RAG parameter tuning (TOP_K, CHUNK_SIZE, CHUNK_OVERLAP)
- Reset to recommended settings

---

## Architecture

### Backend Components

#### 1. Configuration Manager (`backend/config_manager.py`)

**Purpose:** Centralized configuration persistence and Ollama interaction

**Key Functions:**
```python
class SetupConfig:
    def is_setup_completed() -> bool
    def mark_setup_completed() -> None
    def update_models(llm, embedding, translation) -> None
    def update_rag_params(top_k, chunk_size, chunk_overlap) -> None
    def get_config_dict() -> dict

def check_ollama_connection() -> dict
def list_ollama_models() -> dict
def test_model(model_name, model_type) -> dict
```

**Storage:**
- File: `data/config.json`
- Format: JSON with setup status, model names, RAG params
- Default: Falls back to `settings.py` constants

#### 2. Setup Endpoints (`backend/main.py`)

**New API Routes:**
```
GET  /setup/status            # Check if setup completed
GET  /setup/ollama/status     # Check Ollama connection
GET  /setup/ollama/models     # List available models
POST /setup/ollama/test       # Test specific model
POST /setup/complete          # Mark setup as done
POST /config/update           # Update config post-setup
GET  /config/current          # Get current config
```

#### 3. Dynamic Configuration (`backend/settings.py`)

**Enhanced to prioritize:**
1. `data/config.json` (if exists)
2. Environment variables
3. Hardcoded defaults

### Frontend Components

#### 1. Setup Wizard (`frontend/src/components/FirstTimeSetupWizard.tsx`)

**Features:**
- **Connection Check:** Auto-detects Ollama, shows retry button if failed
- **Model Listing:** Categorizes models into LLM vs Embedding
- **Auto-selection:** Defaults to `mistral:instruct` + `bge-m3` if available
- **Model Testing:** "Test" button per model to verify functionality
- **Model Sizes:** Shows model size to help users choose
- **Pull Instructions:** Displays exact commands if no models available
- **Blocking UI:** Cannot skip setup (ensures proper configuration)

**States:**
```typescript
- ollamaStatus: connected | disconnected | error
- models: { llm_models: [], embedding_models: [] }
- selectedLLM: string | null
- selectedEmbedding: string | null
- isTestingModel: boolean
- setupStep: 'checking' | 'selecting' | 'completing'
```

#### 2. Settings Section (`frontend/src/components/SettingsPanel.tsx`)

**Location:** Sidebar → Settings section

**Model Configuration:**
- View current LLM, embedding, translation models
- Dropdown to select different models
- Test button to verify model before switching
- Apply button to save changes

**Advanced Settings (Expandable):**
- TOP_K slider (1-20, default: 5)
- CHUNK_SIZE input (default: 800)
- CHUNK_OVERLAP input (default: 200)
- Reset to recommended button

#### 3. Conditional App Rendering (`frontend/src/App.tsx`)

```tsx
// Check setup status on mount
useEffect(() => {
  const status = await getSetupStatus();
  setSetupCompleted(status.setup_completed);
}, []);

// Render conditionally
return (
  <ErrorBoundary>
    {setupCompleted === false ? (
      <FirstTimeSetupWizard onSetupComplete={() => setSetupCompleted(true)} />
    ) : (
      <MainApp />
    )}
  </ErrorBoundary>
);
```

---

## Configuration File Structure

**File:** `data/config.json`

```json
{
  "setup_completed": true,
  "ollama_models": {
    "llm": "mistral:instruct",
    "embedding": "bge-m3",
    "translation": "mistral:instruct"
  },
  "rag_params": {
    "top_k": 5,
    "chunk_size": 800,
    "chunk_overlap": 200
  }
}
```

**Validation:**
- File created after first setup completion
- All fields have defaults in `settings.py`
- Invalid/missing fields fall back to defaults
- File can be deleted to reset setup state

---

## User Flows

### First-Time User

1. Open app → Setup wizard appears
2. See "Checking Ollama connection..."
3. If Ollama not running:
   - See error message: "Cannot connect to Ollama. Is it running?"
   - Click "Retry" after starting Ollama
4. If Ollama running but no models:
   - See instructions: "Run `ollama pull mistral:instruct`"
   - Click "Refresh Models" after pulling
5. If models available:
   - See auto-selected models (or select manually)
   - Click "Test" to verify (optional)
   - Click "Complete Setup"
6. Configuration saved → Main app loads

### Existing User (Model Switching)

1. Click sidebar → Settings
2. Scroll to "Model Configuration"
3. Click dropdown next to "LLM Model"
4. Select different model
5. Click "Test" to verify
6. If test passes, click "Apply Changes"
7. Configuration updated → App continues using new model

### Power User (Parameter Tuning)

1. Open Settings → Expand "Advanced Settings"
2. Adjust TOP_K slider to 10 (more context)
3. Increase CHUNK_SIZE to 1200
4. Click "Apply Changes"
5. Test with query → Observe results
6. If not better, click "Reset to Recommended"

---

## Ollama Integration

### Connection Testing

```python
def check_ollama_connection() -> dict:
    response = requests.get("http://localhost:11434/api/version", timeout=5)
    return {
        "status": "connected" | "disconnected" | "error",
        "message": "...",
        "version": "0.1.20"  # if connected
    }
```

### Model Listing

```python
def list_ollama_models() -> dict:
    response = requests.get("http://localhost:11434/api/tags", timeout=10)
    models = response.json()["models"]
    
    # Categorize models
    llm_models = [m for m in models if "embed" not in m["name"].lower()]
    embedding_models = [m for m in models if "embed" in m["name"].lower()]
    
    return {
        "llm_models": llm_models,
        "embedding_models": embedding_models
    }
```

### Model Testing

```python
def test_model(model_name: str, model_type: str) -> dict:
    if model_type == "embedding":
        # Test embedding generation
        response = requests.post(".../api/embeddings", json={
            "model": model_name,
            "prompt": "test"
        })
    else:
        # Test LLM generation
        response = requests.post(".../api/generate", json={
            "model": model_name,
            "prompt": "Hello",
            "stream": False
        })
    
    return {"status": "success" | "error", "message": "..."}
```

---

## Alternatives Considered

### Alternative 1: Environment Variables Only

**Description:** Use only `.env` files for configuration

**Pros:** Simple, familiar pattern  
**Cons:** Requires file editing, no validation, poor UX  
**Verdict:** Rejected - not user-friendly

### Alternative 2: CLI Setup Script

**Description:** Run `python setup.py` before starting app

**Pros:** Common pattern, keeps UI simple  
**Cons:** Extra step, disconnected from app, can't validate in real-time  
**Verdict:** Rejected - prefer integrated UX

### Alternative 3: Settings UI Only (No Wizard)

**Description:** Just add settings panel, no first-run wizard

**Pros:** Less code, simpler  
**Cons:** App fails cryptically if models missing, poor first-run UX  
**Verdict:** Rejected - first-run experience critical

### Alternative 4: Auto-Pull Models

**Description:** Automatically download required models on first run

**Pros:** Zero user effort  
**Cons:** Large downloads (4GB+) without consent, assumes user wants specific models  
**Verdict:** Rejected - user should choose models explicitly

### Alternative 5: Hardcode Model Names (Status Quo)

**Description:** Keep models hardcoded in `settings.py`

**Pros:** Simplest approach  
**Cons:** No flexibility, fails if models unavailable, no first-run guidance  
**Verdict:** Rejected - doesn't solve core problems

---

## Consequences

### Positive

* ✅ **Guided onboarding** - New users see clear setup steps
* ✅ **Validation** - Can't proceed without working configuration
* ✅ **Flexibility** - Switch models without code changes
* ✅ **Transparency** - Shows exactly what models are available
* ✅ **Testing** - Verify models work before committing
* ✅ **Persistence** - Configuration survives restarts
* ✅ **Debugging** - Clear error messages if Ollama isn't running
* ✅ **Power user friendly** - Advanced parameters accessible
* ✅ **Reset capability** - Delete config.json to start over

### Negative

* ❌ **Blocking UI** - Can't use app until setup completes (intentional tradeoff)
* ❌ **More code** - ~500 lines for setup wizard + config manager
* ❌ **File dependency** - Relies on `data/config.json` existing
* ❌ **Model switching overhead** - Requires reingestion if embedding model changes

### Neutral

* 📊 Setup wizard adds ~2 minutes on first run
* 📊 Configuration file is human-readable JSON (can edit manually)
* 📊 Ollama API calls add minimal latency (<100ms)

---

## Migration Notes

### For New Installations

1. Start app → Setup wizard appears automatically
2. Follow wizard steps
3. Configuration saved, main app loads

### For Existing Installations (Pre-ADR-014)

1. No `data/config.json` exists → Setup wizard appears
2. Complete wizard (selects currently configured models by default)
3. Configuration persisted, app behavior unchanged

### For Developers

1. New dependency: `requests` library (already in requirements.txt)
2. New module: `backend/config_manager.py`
3. New component: `frontend/src/components/FirstTimeSetupWizard.tsx`
4. Updated: `backend/main.py` (setup endpoints)
5. Updated: `frontend/src/App.tsx` (conditional rendering)

---

## Implementation Status

**Backend:**
- [x] Create `config_manager.py` module
- [x] Implement `SetupConfig` class
- [x] Add Ollama connection check
- [x] Add model listing endpoint
- [x] Add model testing endpoint
- [x] Add setup completion endpoint
- [x] Add configuration update endpoint
- [x] Integrate with `settings.py`

**Frontend:**
- [x] Create `FirstTimeSetupWizard.tsx` component
- [x] Design wizard UI (connection check, model selection, completion)
- [x] Implement conditional rendering in `App.tsx`
- [x] Add setup API client functions
- [x] Add Settings section to sidebar
- [x] Add model configuration UI in SettingsPanel
- [x] Add advanced RAG parameters UI
- [x] Add "Test Model" functionality

**Testing:**
- [x] Test first-run experience
- [x] Test model switching
- [x] Test configuration persistence
- [x] Test Ollama connection failure scenarios
- [x] Test no models available scenario

---

## Future Enhancements

### 1. Multi-Step Setup (Expanded Wizard)

**Step 2: Import Backup** (optional)
- Import existing `config.json` and `vectordb/`
- Skip manual re-upload
- Faster setup for migrating users

**Step 3: Advanced Configuration** (optional)
- Set RAG parameters during setup
- Choose data directory location
- Configure logging level

### 2. Model Auto-Update

Check for model updates periodically:
```
"New version of mistral:instruct available. Update now?"
```

### 3. Model Recommendations

Suggest models based on use case:
- **Small manuals (<100 pages):** Smaller, faster models
- **Large manuals (>500 pages):** Larger, more accurate models
- **Multilingual:** Models with better translation

### 4. Configuration Export/Import

```
[Export Config] → Downloads config + catalog + vector DB
[Import Config] → Restores from backup
```

### 5. Health Check Dashboard

Regular checks:
- Ollama running?
- Models still available?
- Disk space sufficient?
- Vector DB integrity?

### 6. Model Performance Metrics

Track and display:
- Average query response time
- Retrieval accuracy
- Model switch history

---

## Related Decisions

* **ADR-001:** Local-first architecture (Ollama integration)
* **ADR-011:** Settings panel (location for configuration UI)
* **ADR-013:** Code quality and centralized configuration (sets precedent)

---

## References

* `backend/config_manager.py` - Configuration persistence
* `frontend/src/components/FirstTimeSetupWizard.tsx` - Setup UI
* `frontend/src/components/SettingsPanel.tsx` - Settings UI (model config section)
* `data/config.json` - Configuration file schema
* [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)

---

## Notes

**Why block the app during setup?**
- Ensures configuration is valid before allowing queries
- Prevents confusing errors from missing models
- Forces users to complete setup (better than silent failures)
- Clear separation: setup → usage

**Why test models before accepting?**
- Model may be corrupted
- Ollama may have issues loading it
- Better to catch problems during setup than during usage
- Gives user confidence that configuration works

**Why persist to file vs database?**
- Simple, human-readable JSON
- No database schema evolution needed
- Easy to backup (just copy file)
- Can be version controlled
- Fast to read/write

**Why allow model switching post-setup?**
- Models improve over time (new releases)
- Users may want to try different models
- Experimentation is valuable
- Power users need flexibility

**Configuration hierarchy (precedence):**
1. `data/config.json` (if exists)
2. Environment variables (if set)
3. Hardcoded defaults in `settings.py`

This allows maximum flexibility while maintaining sensible defaults.

