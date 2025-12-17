#!/usr/bin/env bash
# Restart Backend Service
# This script restarts the backend API server

set -euo pipefail

# Parse command line arguments
EXPOSE_NETWORK=0
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--network|network)
      EXPOSE_NETWORK=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-n|--network]"
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Restarting Backend API..."

# Try to find and stop existing backend process
BACKEND_PID=$(pgrep -f "uvicorn.*backend.main" || true)

if [ -n "$BACKEND_PID" ]; then
    echo "[INFO] Stopping existing backend process (PID: $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
    sleep 2
    # Force kill if still running
    kill -9 "$BACKEND_PID" 2>/dev/null || true
    echo "[OK] Backend stopped"
fi

# Pick python (prefer backend venv)
BACKEND_PY=""
if [[ -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  BACKEND_PY="$ROOT_DIR/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  BACKEND_PY="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  BACKEND_PY="$(command -v python)"
else
  echo "[ERROR] Python not found. Install Python 3.11+ and retry."
  exit 1
fi

# Determine host binding
if [ "$EXPOSE_NETWORK" -eq 1 ]; then
  HOST_BINDING="0.0.0.0"
else
  HOST_BINDING="127.0.0.1"
fi

# Start backend
echo "[INFO] Starting Backend API (port 8000)..."
(cd "$ROOT_DIR/backend" && EXPOSE_NETWORK="$EXPOSE_NETWORK" "$BACKEND_PY" -m uvicorn backend.main:app --reload --host "$HOST_BINDING" --port 8000) &

echo "[OK] Backend restarted (PID: $!)"
echo ""
echo "Backend API: http://localhost:8000"
if [ "$EXPOSE_NETWORK" -eq 1 ]; then
  echo "Network access enabled"
fi

