#!/usr/bin/env bash
# Start backend (FastAPI) + frontend (Next.js) for local development.
# Prerequisites: backend/venv + pip install; frontend npm install.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PY="$BACKEND/venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Missing backend virtualenv. Run:"
  echo "  cd backend && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "Missing frontend dependencies. Run:"
  echo "  cd frontend && npm install"
  exit 1
fi

for p in 8000 3000; do
  if lsof -i ":$p" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    echo "Port $p is already in use. Stop the other process or free the port, then retry."
    exit 1
  fi
done

cleanup() {
  kill "${BACK_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:8000 ..."
cd "$BACKEND"
"$PY" -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACK_PID=$!

echo "Waiting for backend /health ..."
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
    break
  fi
  sleep 0.3
done
if ! curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
  echo "Backend did not become healthy in time. Check logs above."
  exit 1
fi

echo "Starting frontend on http://127.0.0.1:3000 ..."
cd "$FRONTEND"
exec npm run dev
