#!/bin/bash
set -e

# Default to SQLite when no external DB is configured
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////tmp/officepulse.db}"
export MCP_HOST="127.0.0.1"
export MCP_PORT="8001"
export BACKEND_HOST="127.0.0.1"
export BACKEND_PORT="8000"
export CORS_ORIGINS="*"
export TZ="${TZ:-Asia/Dhaka}"
export OFFICE_OPEN="${OFFICE_OPEN:-09:00}"
export OFFICE_CLOSE="${OFFICE_CLOSE:-17:00}"
export SIM_TICK_SECONDS="${SIM_TICK_SECONDS:-5}"
export DEMO_MODE="${DEMO_MODE:-false}"

echo "=== OfficePulse starting ==="
echo "DATABASE_URL: $DATABASE_URL"

# Start FastAPI backend
cd /app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info &
BACKEND_PID=$!

# Wait for backend to be healthy
echo "Waiting for backend..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "Backend ready after ${i}s"
        break
    fi
    sleep 1
done

# Start MCP server
cd /app
python mcp_server/server.py &
MCP_PID=$!

echo "Starting nginx on :7860"
nginx -g "daemon off;" &
NGINX_PID=$!

# Keep container alive; exit if any critical process dies
wait -n $BACKEND_PID $MCP_PID $NGINX_PID
echo "A service exited — shutting down"
kill $BACKEND_PID $MCP_PID $NGINX_PID 2>/dev/null || true
