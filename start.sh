#!/usr/bin/env bash
# ==============================================================================
# codewise startup script
# understand the code. master the logic.
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "========================================================"
echo " Starting codewise"
echo " understand the code. master the logic."
echo "========================================================"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
    echo "Error: Node.js is not installed or not in PATH."
    exit 1
fi

# Setup backend venv if not present
if [ ! -d "backend/venv" ]; then
    echo "Setting up Python virtual environment in backend/venv..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    pip install -r backend/requirements.txt
else
    source backend/venv/bin/activate
fi

# Setup frontend node_modules if not present
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Start Backend on port 8000
echo "Starting codewise backend on http://127.0.0.1:8000..."
export PYTHONPATH="$PROJECT_ROOT"
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PROJECT_ROOT/.codewise.pid"

# Trap interrupt to kill background processes
trap "echo 'Stopping codewise...'; kill $BACKEND_PID 2>/dev/null || true; rm -f '$PROJECT_ROOT/.codewise.pid'; exit 0" INT TERM EXIT

# Start Frontend on port 5173
echo "Starting codewise frontend on http://localhost:5173..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
