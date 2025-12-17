#!/usr/bin/env bash
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
      echo "  -n, --network: Expose services to local network (default: localhost only)"
      echo ""
      echo "Examples:"
      echo "  $0              # Start with localhost only"
      echo "  $0 -n           # Expose to local network"
      echo "  $0 --network    # Expose to local network"
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Starting Home Manual Assistant Services..."
if [ "$EXPOSE_NETWORK" -eq 1 ]; then
  echo "[INFO] Network exposure enabled - services will be accessible from local network"
else
  echo "[INFO] Localhost only - use -n or --network flag to expose to local network"
fi
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
if [ "$EXPOSE_NETWORK" -eq 1 ]; then
  HOST_BINDING="0.0.0.0"
else
  HOST_BINDING="127.0.0.1"
fi
(cd "$ROOT_DIR/backend" && EXPOSE_NETWORK="$EXPOSE_NETWORK" "$BACKEND_PY" -m uvicorn backend.main:app --reload --host "$HOST_BINDING" --port 8000) &
BACKEND_PID=$!
echo "[OK] Backend starting (pid $BACKEND_PID)"

echo ""

echo "[INFO] Starting Frontend Dev Server (port 5173)..."
if [ "$EXPOSE_NETWORK" -eq 1 ]; then
  (cd "$ROOT_DIR/frontend" && VITE_EXPOSE_NETWORK=1 npm run dev) &
else
  (cd "$ROOT_DIR/frontend" && npm run dev) &
fi
FRONTEND_PID=$!
echo "[OK] Frontend starting (pid $FRONTEND_PID)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[OK] All services starting!"
echo ""
echo "Local access:"
echo "  Backend API:  http://localhost:8000"
echo "  Frontend UI:  http://localhost:5173"
if [ "$EXPOSE_NETWORK" -eq 1 ]; then
  echo ""
  echo "Network access (from other devices on your local network):"
  # Try to detect local IP address
  if command -v hostname >/dev/null 2>&1 && command -v ip >/dev/null 2>&1; then
      # Linux: try to get IP from ip command
      NETWORK_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n1)
  elif command -v ifconfig >/dev/null 2>&1; then
      # macOS/BSD: try to get IP from ifconfig
      NETWORK_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n1)
  fi

  if [ -n "$NETWORK_IP" ]; then
      echo "  Backend API:  http://${NETWORK_IP}:8000"
      echo "  Frontend UI:  http://${NETWORK_IP}:5173"
  else
      echo "  (Run 'ip addr' or 'ifconfig' to find your local IP address)"
  fi
fi
echo ""
echo "Press Ctrl+C to stop services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

wait


