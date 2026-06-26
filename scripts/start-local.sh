#!/usr/bin/env bash
# Start Graph Builder backend + frontend for local dev (separate terminals recommended).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama is not running. Start it with: ollama serve"
  exit 1
fi

echo "Starting backend on http://localhost:8001"
cd "$ROOT/backend"
source venv/bin/activate
uvicorn score:app --reload --port 8001 &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:5173"
cd "$ROOT/frontend"
yarn run dev &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT
wait
