#!/usr/bin/env bash
# ==============================================================================
# codewise shutdown script
# understand the code. master the logic.
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "========================================================"
echo " Stopping codewise services"
echo "========================================================"

STOPPED_ANY=false

# 1. Stop recorded PID if present
if [ -f ".codewise.pid" ]; then
    PID=$(cat .codewise.pid)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "Stopping backend process (PID $PID)..."
        kill "$PID" 2>/dev/null || true
        STOPPED_ANY=true
    fi
    rm -f .codewise.pid
fi

# 2. Terminate any remaining backend processes on port 8000
BACKEND_PIDS=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "Terminating process(es) on port 8000: $BACKEND_PIDS"
    echo "$BACKEND_PIDS" | xargs kill 2>/dev/null || true
    STOPPED_ANY=true
fi

# 3. Terminate any remaining frontend processes on port 5173
FRONTEND_PIDS=$(lsof -ti :5173 2>/dev/null || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "Terminating process(es) on port 5173: $FRONTEND_PIDS"
    echo "$FRONTEND_PIDS" | xargs kill 2>/dev/null || true
    STOPPED_ANY=true
fi

# 4. Fallback search for uvicorn or vite codewise processes
pkill -f "uvicorn backend.app.main:app" 2>/dev/null || true

if [ "$STOPPED_ANY" = true ]; then
    echo "All codewise services have been stopped successfully."
else
    echo "No running codewise services were found on ports 8000 or 5173."
fi

echo "Your saved sessions and database in data/codewise.db are fully preserved."
