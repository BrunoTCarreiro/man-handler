## Home Manual Assistant

A fully local RAG (Retrieval-Augmented Generation) system for home appliance and furniture manuals:

- **LLM + Embeddings:** Ollama with `mistral:instruct` + `bge-m3` (multilingual)
- **Backend:** FastAPI + LangChain + ChromaDB (`backend/`)
- **Frontend:** React + TypeScript + Vite (`frontend/`)
- **OCR:** DeepSeek-OCR with smart language detection
- **Data:** Manuals stored as markdown + vector embeddings (`data/`)

Features automatic language detection, selective extraction (60-70% time savings), background processing with cancellation, and comprehensive device management.

---

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (npm included)
- [Ollama](https://ollama.com) running locally:
  ```bash
  ollama pull mistral:instruct
  ollama pull bge-m3
  ```

---

### 2. One-time setup

#### Backend environment
**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

**macOS/Linux (bash/zsh)**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

#### Frontend dependencies
**Windows (PowerShell)**

```powershell
cd frontend
npm install
cd ..
```

**macOS/Linux (bash/zsh)**

```bash
cd frontend
npm install
cd ..
```

#### Initial data structure
The app will automatically create these on first run:
- `data/catalog/devices.json` - Device metadata
- `data/manuals/` - Manual files (PDFs + markdown)
- `data/vectordb/` - ChromaDB embeddings

No manual setup required! Use the UI to upload manuals via the wizard.

---

### 3. Daily run

**Quick start (recommended):**

**Windows**
```powershell
# PowerShell - localhost only (default)
.\start-services.ps1

# PowerShell - expose to local network
.\start-services.ps1 -Network
# or
.\start-services.ps1 -n

# Or use the batch file
start-services.bat          # localhost only
start-services.bat network  # expose to network
```

**macOS/Linux**

```bash
chmod +x ./start-services.sh

# Localhost only (default)
./start-services.sh

# Expose to local network
./start-services.sh --network
# or
./start-services.sh -n
```

This will automatically start all three services (Ollama, Backend, Frontend). On Windows it opens separate terminals; on macOS/Linux it runs everything from your current terminal (Ctrl+C to stop).

**Network Access:** By default, services are only accessible on `localhost`. Use the `-Network` flag (or `-n`) to expose services to your local network, allowing other devices to access the app.

**Restart Backend:** If the backend crashes, you can restart it using:
- Windows: `.\restart-backend.ps1 [-Network]`
- Linux/macOS: `./restart-backend.sh [-n|--network]`

Or use the REST API endpoint: `POST /restart` (triggers graceful shutdown; process manager should restart it).

#### Environment Variables

##### Backend Configuration

Create a `backend/.env` file (see `backend/env.example`):

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# CORS: Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Ollama Model Configuration
EMBED_MODEL=bge-m3
LLM_MODEL=mistral:instruct
TRANSLATION_MODEL=mistral:instruct

# RAG Retrieval Parameters
TOP_K=5
RELEVANCE_THRESHOLD=0.3

# Text Chunking Configuration
CHUNK_SIZE=800
CHUNK_OVERLAP=200
```

##### Frontend Configuration

Create `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

**Manual start (alternative):**
1. **Start the backend API**

   **Windows (PowerShell)**

   ```powershell
   backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

   **macOS/Linux (bash/zsh)**

   ```bash
   cd backend
   . .venv/bin/activate
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend dev server**

   ```bash
   cd frontend
   npm run dev
   ```
3. Browse to `http://localhost:5173` (backend listens on `http://localhost:8000`).

---

### 3.1 Notes for macOS/Linux

- If `pip install -r backend/requirements.txt` fails on `reportlab`, you can install system deps first:
  - **macOS (Homebrew)**: `brew install freetype libjpeg`
  - **Debian/Ubuntu**: `sudo apt-get install -y libfreetype6-dev libjpeg-dev zlib1g-dev`
  - Or remove `reportlab` from `backend/requirements.txt` (it’s treated as optional at runtime).

---

### 4. Usage

#### Adding a Manual (4-Step Wizard)

Click the **"Add Manual"** button in the header to open the onboarding wizard:

1. **Select File** – Drag & drop or choose a PDF manual (multilingual OK).

2. **Process Manual** – Automatic processing in background:
   - Pre-scans PDF for language sections
   - Detects longest English section (or easiest to translate)
   - OCR extracts only relevant pages (~6 sec/page)
   - Translates to English if needed
   - Generates clean markdown reference file
   - Real-time log updates (polls every 3 seconds)
   - Cancel anytime (stops after current page)

3. **Analyze with AI** – Automatically extracts metadata:
   - Device name, brand, model
   - Room location, category
   - Pre-fills form for review/editing

4. **Upload to Knowledge Base** – Confirm and commit:
   - Saves to `data/manuals/<device_id>/`
   - Embeds markdown into ChromaDB
   - Device appears in dropdown immediately

**Background Processing:** UI stays responsive during OCR. Progress logs stream in real-time.

**Smart Language Detection:** Only processes English sections (or smallest translation job), saving 60-70% time on multilingual manuals.

#### Asking Questions

1. Select a device from the dropdown (grouped by room) in the input bar
2. Type your question: "How do I clean the filter?"
3. LLM retrieves relevant manual sections and answers
4. Sources cited with page numbers

#### Managing Devices (Settings Panel)

Click **"Settings"** button to open the management panel:

**Device Actions (dropdown):**
Click "Actions" on any device to access:
- **View Manual** - Display processed markdown in scrollable modal
  - Inspect translation quality
  - Verify content extraction
  - Debug RAG retrieval issues
- **Edit Metadata** - Update name, brand, model, room, or category
- **Replace Manual** - Upload new PDF via wizard (replaces existing)
  - Upload better quality scan
  - Replace with updated version
  - Fix translation errors with new source
- **Delete Device** - Remove device completely (files, embeddings, metadata)

**Room Management:**
- Click "Edit" on room header to rename
- All devices in that room update automatically

**Database Reset:**
- Nuclear option to clear everything
- Confirmation required

---

### 5. API Reference

**Manual Processing:**
```bash
# Start processing (returns token immediately)
curl -F file=@manual.pdf http://localhost:8000/manuals/process

# Poll status (every 3 seconds)
curl http://localhost:8000/manuals/process/status/{token}

# Cancel processing
curl -X POST http://localhost:8000/manuals/process/cancel/{token}

# Analyze with AI
curl -X POST -H "Content-Type: application/json" \
  -d '{"token":"<token>"}' http://localhost:8000/manuals/analyze

# Commit to database
curl -X POST -H "Content-Type: application/json" \
  -d '{"token":"<token>","manual_filename":"<file>","metadata":{...}}' \
  http://localhost:8000/manuals/commit
```

**Device Management:**
```bash
# Get all devices
curl http://localhost:8000/devices

# Get device markdown content
curl http://localhost:8000/devices/{device_id}/markdown

# Get a device file (images are stored under images/)
curl http://localhost:8000/devices/{device_id}/files/images/page_005_image_1.png

# Update device metadata
curl -X PATCH -H "Content-Type: application/json" \
  -d '{"name":"New Name","brand":"Brand","model":"Model","room":"kitchen","category":"appliance"}' \
  http://localhost:8000/devices/{device_id}

# Replace device manual (re-ingest)
curl -X POST http://localhost:8000/devices/{device_id}/replace

# Delete device
curl -X DELETE http://localhost:8000/devices/{device_id}

# Rename room
curl -X POST -H "Content-Type: application/json" \
  -d '{"old_room":"office","new_room":"home office"}' \
  http://localhost:8000/devices/rooms/rename
```

**Chat:**
```bash
# Ask a question
curl -X POST -H "Content-Type: application/json" \
  -d '{"question":"How do I clean the filter?","device_id":"abc123"}' \
  http://localhost:8000/chat
```

**Full API docs:** http://localhost:8000/docs (FastAPI Swagger UI)

---

### 6. Architecture

See `docs/adr/` for all architectural decision records:
- **ADR-001:** Local-first architecture (Ollama)
- **ADR-008:** Modal wizard UX
- **ADR-009:** Language section detection (60-70% time savings)
- **ADR-010:** Markdown-first ingestion
- **ADR-011:** Settings panel and device management
- **ADR-012:** Actions dropdown and view manual feature

**Key files:**
- `backend/main.py` - FastAPI app, all endpoints
- `backend/language_detection.py` - Smart language pre-scan
- `backend/ocr_extraction.py` - DeepSeek-OCR integration
- `backend/ingest.py` - ChromaDB operations
- `frontend/src/components/ManualOnboardingModal.tsx` - 4-step wizard
- `frontend/src/components/SettingsPanel.tsx` - Device management with actions dropdown
- `frontend/src/components/ViewManualModal.tsx` - View processed markdown
- `frontend/src/components/EditDeviceModal.tsx` - Edit device metadata

---

### 7. Troubleshooting

**Processing is slow**  
→ OCR takes ~6 seconds per page (API-bound). Language detection reduces pages processed by 60-70%.

**Bad translation in manual**  
→ Edit `data/manuals/<device_id>/*_reference.md` manually, then click "Replace" in settings to re-ingest.

**Device not appearing**  
→ Check `data/catalog/devices.json` exists and contains the device. Check logs for errors.

**Empty LLM responses**  
→ Verify `data/vectordb/` has embeddings. Try "Reset Database" in settings and re-upload manuals.

**Modal crashes after reset**  
→ Browser console may show token errors. Refresh page. (Processing tokens cleared on reset.)

**Cancel button doesn't work**  
→ It waits for current page to finish (~6s). Check logs for "[INFO] Processing cancelled at page X/Y".

---

### 8. Sharing with Others

```bash
# Create zip (respects .gitignore)
git archive --format=zip --output home-manual-assistant.zip HEAD
```

Recipients should:
1. Extract zip
2. Follow setup instructions (sections 1-3)
3. Upload their own manuals via UI
4. No manual data setup required!

