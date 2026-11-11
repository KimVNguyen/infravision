#!/bin/sh
set -e

if [ "$DEV_MODE" = "true" ] || [ "$DEV_MODE" = "1" ]; then
    echo "[Infravision Backend] DEV_MODE=true: Starting Uvicorn with Hot Reload watching /app/src..."
    exec uvicorn infravision.api.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src
else
    echo "[Infravision Backend] DEV_MODE=false: Starting Uvicorn in production mode (no reloader)..."
    exec uvicorn infravision.api.app:app --host 0.0.0.0 --port 8000 --workers 2
fi
