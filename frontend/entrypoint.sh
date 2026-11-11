#!/bin/sh
set -e

if [ "$DEV_MODE" = "true" ] || [ "$DEV_MODE" = "1" ]; then
    echo "[Infravision Frontend] DEV_MODE=true: Starting Vite development server with Hot Module Replacement..."
    exec npm run dev -- --host 0.0.0.0 --port 5173
else
    echo "[Infravision Frontend] DEV_MODE=false: Building and serving optimized production bundle..."
    npm run build
    exec npm run preview -- --host 0.0.0.0 --port 5173
fi
