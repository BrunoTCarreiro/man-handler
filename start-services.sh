#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Starting Home Manual Assistant Services..."
echo ""

have_cmd() { command -v "$1" >/dev/null 2>&1; }

ollama_running() {
  if have_cmd curl; then
    curl -fsS "http://localhost:11434/api/tags" >/dev/null 2>&1
    return $?
  fi
  if have_cmd pgrep; then
    pgrep -x "ollama" >/dev/null 2>&1
    return $?
  fi
  return 1
}

# Start Ollama (if installed and not already running)
if have_cmd ollama; then
  if ollama_running; then
    echo "[OK] Ollama already running"
  else
    echo "[INFO] Starting Ollama service..."
    (ollama serve >/dev/null 2>&1 &)
    sleep 2
    echo "[OK] Ollama started"
  fi
else
  echo "[WARN] Ollama not found on PATH. Install it from https://ollama.com and run: ollama serve"
fi

echo ""

# Pick python (prefer backend venv)
BACKEND_PY=""
if [[ -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  BACKEND_PY="$ROOT_DIR/backend/.venv/bin/python"
elif have_cmd python3; then
  BACKEND_PY="$(command -v python3)"
elif have_cmd python; then
  BACKEND_PY="$(command -v python)"
else
  echo "[ERROR] Python not found. Install Python 3.11+ and retry."
  exit 1
fi

cleanup() {
  echo ""
  echo "Stopping services..."
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "$BACKEND_PID" >/dev/null 2>&1 || true; fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then kill "$FRONTEND_PID" >/dev/null 2>&1 || true; fi
}
trap cleanup INT TERM EXIT

echo "[INFO] Starting Backend API (port 8000)..."
(cd "$ROOT_DIR" && "$BACKEND_PY" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!
echo "[OK] Backend starting (pid $BACKEND_PID)"

echo ""

echo "[INFO] Starting Frontend Dev Server (port 5173)..."
(cd "$ROOT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!
echo "[OK] Frontend starting (pid $FRONTEND_PID)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[OK] All services starting!"
echo ""
echo "Backend API:  http://localhost:8000"
echo "Frontend UI:  http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

wait


