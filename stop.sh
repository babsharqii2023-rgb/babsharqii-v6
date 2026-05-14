#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# BABSHARQII v40.0 "Mamoun" — Stop All Services
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

LOG_DIR="$(cd "$(dirname "$0")" && pwd)/logs"

# Kill from PID file
if [ -f "$LOG_DIR/pids.txt" ]; then
    PIDS=$(cat "$LOG_DIR/pids.txt")
    for PID in $PIDS; do
        kill "$PID" 2>/dev/null && echo "Killed PID $PID" || echo "PID $PID not running"
    done
    rm "$LOG_DIR/pids.txt"
fi

# Kill by port
for port in 8000 3000; do
    OLD_PID=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$OLD_PID" ]; then
        kill $OLD_PID 2>/dev/null && echo "Killed process on port $port" || true
    fi
done

echo "All services stopped."
