#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# BABSHARQII v23.0 — Mamoun Startup Script
# سكريبت التشغيل مع إعادة التشغيل التلقائي
#
# Features:
#   - Auto-restart on crash (up to 10 times)
#   - Health monitoring
#   - Graceful shutdown
#   - Process management
# ═══════════════════════════════════════════════════════════════════════════════

set -e

PROJECT_DIR="/home/z/my-project/backend"
PID_FILE="/home/z/my-project/backend/mamoun.pid"
LOG_FILE="/home/z/my-project/backend/mamoun.log"
MAX_RESTARTS=10
RESTART_DELAY=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   BABSHARQII v23.0 — Mamoun Living AI System${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Kill existing process if running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}[Mamoun] Stopping existing process (PID: $OLD_PID)...${NC}"
        kill -TERM "$OLD_PID" 2>/dev/null || true
        sleep 2
        # Force kill if still running
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
fi

cd "$PROJECT_DIR"

# Function to run the server with auto-restart
run_server() {
    local restart_count=0
    local start_time=$(date +%s)

    while [ $restart_count -lt $MAX_RESTARTS ]; do
        echo -e "${GREEN}[Mamoun] Starting server (attempt $((restart_count + 1))/$MAX_RESTARTS)...${NC}"
        echo -e "${GREEN}[Mamoun] Log: $LOG_FILE${NC}"

        # Run uvicorn
        python -m uvicorn mamoun.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 1 \
            --log-level info \
            --no-access-log \
            2>&1 | tee -a "$LOG_FILE" &

        SERVER_PID=$!
        echo $SERVER_PID > "$PID_FILE"

        echo -e "${GREEN}[Mamoun] Server started (PID: $SERVER_PID)${NC}"
        echo -e "${CYAN}[Mamoun] API: http://localhost:8000${NC}"
        echo -e "${CYAN}[Mamoun] Docs: http://localhost:8000/docs${NC}"
        echo -e "${CYAN}[Mamoun] Health: http://localhost:8000/health${NC}"

        # Wait for server to exit
        wait $SERVER_PID 2>/dev/null
        EXIT_CODE=$?

        # Remove PID file
        rm -f "$PID_FILE"

        # Check if it was a clean shutdown
        if [ $EXIT_CODE -eq 0 ]; then
            echo -e "${GREEN}[Mamoun] Clean shutdown.${NC}"
            break
        fi

        # Crash detected
        restart_count=$((restart_count + 1))
        echo -e "${RED}[Mamoun] Server crashed (exit code: $EXIT_CODE)${NC}"
        echo -e "${YELLOW}[Mamoun] Restarting in ${RESTART_DELAY}s... ($restart_count/$MAX_RESTARTS)${NC}"

        sleep $RESTART_DELAY

        # Increase delay for subsequent restarts (exponential backoff)
        RESTART_DELAY=$((RESTART_DELAY * 2))
        if [ $RESTART_DELAY -gt 60 ]; then
            RESTART_DELAY=60
        fi
    done

    if [ $restart_count -ge $MAX_RESTARTS ]; then
        echo -e "${RED}[Mamoun] Max restarts reached ($MAX_RESTARTS). Stopping.${NC}"
        exit 1
    fi
}

# Handle signals
trap 'echo -e "${YELLOW}[Mamoun] Shutdown signal received...${NC}"; kill $(cat "$PID_FILE" 2>/dev/null) 2>/dev/null; exit 0' SIGTERM SIGINT

# Start the server
run_server
