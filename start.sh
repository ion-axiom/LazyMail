#!/usr/bin/env bash
# LazyMail Quick Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

# Check if port 8000 is in use and offer clean release
EXISTING_PID=$(lsof -ti :8000 || true)
if [ -n "$EXISTING_PID" ]; then
    echo "Notice: Port 8000 is currently occupied by PID $EXISTING_PID. Freeing port..."
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

echo "=================================================="
echo "          LazyMail Client Starting                "
echo "=================================================="
echo "Server URL: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop."
echo "=================================================="

PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
