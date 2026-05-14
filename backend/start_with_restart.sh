#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# BABSHARQII v23.0 — Enhanced Backend Start Script with Process Manager
# سكريبت التشغيل المحسّن مع مدير العمليات
#
# Uses process_manager.py for:
#   - Auto-restart with exponential backoff (5s → 10s → 20s → 40s → 60s max)
#   - Health monitoring
#   - State persistence
#   - Max 10 restarts before giving up
#
# Usage:
#   ./start_with_restart.sh              # Start with process manager
#   ./start_with_restart.sh --direct     # Start directly (no process manager)
#   ./start_with_restart.sh --stop       # Stop backend
#   ./start_with_restart.sh --status     # Check status
#   ./start_with_restart.sh --restart    # Force restart
#   ./start_with_restart.sh --log        # Tail the log
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}"
LOG_DIR="${BACKEND_DIR}/logs"
PID_FILE="${BACKEND_DIR}/.process_manager.pid"
BACKEND_PID_FILE="${BACKEND_DIR}/mamoun.pid"
STATE_FILE="${BACKEND_DIR}/.restart_state.json"

# ─── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

log_info()  { echo -e "  ${CYAN}ℹ${NC}  $*"; }
log_ok()    { echo -e "  ${GREEN}✓${NC}  $*"; }
log_warn()  { echo -e "  ${YELLOW}!${NC}  $*"; }
log_err()   { echo -e "  ${RED}✗${NC}  $*"; }

# ─── Ensure directories ───────────────────────────────────────────────────────
mkdir -p "${LOG_DIR}" "${BACKEND_DIR}/data" "${BACKEND_DIR}/sandbox" "${BACKEND_DIR}/backups"

# ─── Check if process manager is running ──────────────────────────────────────
is_manager_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    return 1
}

# ─── Check if backend is running ──────────────────────────────────────────────
is_backend_running() {
    # Check via health endpoint first
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        return 0
    fi
    # Check via PID file
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid
        pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    return 1
}

# ─── Stop backend ─────────────────────────────────────────────────────────────
stop_backend() {
    log_info "Stopping backend..."

    # Stop process manager first
    if is_manager_running; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        log_info "Stopping process manager (PID: ${pid})..."
        kill "$pid" 2>/dev/null || true
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            log_warn "Force-killing process manager..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        log_ok "Process manager stopped"
    fi

    # Kill any orphan uvicorn processes
    pkill -f "uvicorn mamoun.main:app" 2>/dev/null || true
    sleep 1

    # Clean up PID files
    rm -f "$BACKEND_PID_FILE" 2>/dev/null || true

    log_ok "Backend stopped"
}

# ─── Status ───────────────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}   BABSHARQII v23.0 — Backend Status${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""

    # Process manager status
    if is_manager_running; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        log_ok "Process Manager: RUNNING (PID: ${pid})"
    else
        log_err "Process Manager: NOT RUNNING"
    fi

    # Backend health
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_ok "Backend: HEALTHY"
        local health
        health=$(curl -s http://localhost:8000/health 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Status: {data.get('status', 'unknown')}\")
    print(f\"  Version: {data.get('version', 'unknown')}\")
    print(f\"  Brains: {len(data.get('brains', {}))} active\")
    print(f\"  Kernel: {data.get('kernel_running', False)}\")
except: print('  (could not parse health response)')
" 2>/dev/null || echo "  (health check available but could not parse)")
        echo -e "${DIM}${health}${NC}"
    else
        log_err "Backend: NOT RESPONDING"
    fi

    # Restart state
    if [ -f "$STATE_FILE" ]; then
        echo ""
        log_info "Restart State:"
        python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        state = json.load(f)
    print(f\"  Total Restarts: {state.get('total_restarts', 0)}\")
    print(f\"  Status: {state.get('status', 'unknown')}\")
    print(f\"  Health Failures: {state.get('consecutive_health_failures', 0)}\")
    print(f\"  Current Backoff: {state.get('current_backoff', 0)}s\")
    recent = state.get('recent_restarts', [])
    if recent:
        print(f\"  Last Restart: {recent[0].get('reason', 'unknown')} at {recent[0].get('timestamp', 'unknown')}\")
except Exception as e:
    print(f'  Error reading state: {e}')
" 2>/dev/null || echo "  (could not read state file)"
    fi

    echo ""
}

# ─── Start with Process Manager ──────────────────────────────────────────────
start_with_manager() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}BABSHARQII v23.0 \"Mamoun\" — Backend${NC}                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}Process Manager Mode • Auto-Restart • Health Monitor${NC}      ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Host: 0.0.0.0:8000                                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  API:  http://localhost:8000/docs                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Log:  ${LOG_DIR}/process_manager.log                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Max Restarts: 10 • Backoff: 5s→10s→20s→40s→60s            ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  Stop:  ./start_with_restart.sh --stop                      ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  Ctrl+C also stops gracefully (Law 5)                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if is_manager_running; then
        log_warn "Process manager is already running"
        show_status
        return 1
    fi

    # Start the process manager
    cd "${BACKEND_DIR}"
    export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH:-}"

    log_info "Starting process manager..."
    python3 "${BACKEND_DIR}/process_manager.py" start
}

# ─── Start Direct (no process manager) ────────────────────────────────────────
start_direct() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}BABSHARQII v23.0 \"Mamoun\" — Backend (Direct)${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}No Process Manager • Single Instance${NC}                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if is_backend_running; then
        log_warn "Backend is already running"
        return 1
    fi

    cd "${BACKEND_DIR}"
    export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH:-}"

    log_info "Starting uvicorn directly..."
    python3 -m uvicorn mamoun.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --log-level info \
        --no-access-log \
        2>&1 | tee -a "${LOG_DIR}/backend.log"
}

# ─── Tail logs ────────────────────────────────────────────────────────────────
tail_log() {
    local log_file="${LOG_DIR}/process_manager.log"
    if [ ! -f "$log_file" ]; then
        log_file="${LOG_DIR}/backend.log"
    fi
    if [ -f "$log_file" ]; then
        log_info "Tailing ${log_file}..."
        tail -f "$log_file"
    else
        log_err "No log file found"
    fi
}

# ─── Route ────────────────────────────────────────────────────────────────────
case "${1:-}" in
    --direct|-d)
        start_direct
        ;;
    --stop|-s)
        stop_backend
        ;;
    --status)
        show_status
        ;;
    --restart|-r)
        stop_backend
        sleep 2
        start_with_manager
        ;;
    --log|-l)
        tail_log
        ;;
    --help|-h)
        echo ""
        echo -e "${BOLD}BABSHARQII v23.0 — Backend Start Script${NC}"
        echo ""
        echo "Usage: $0 [FLAG]"
        echo ""
        echo "Flags:"
        echo "  (none)     Start backend with process manager (auto-restart)"
        echo "  --direct   Start directly without process manager"
        echo "  --stop     Stop the backend"
        echo "  --status   Check if backend is running"
        echo "  --restart  Force restart"
        echo "  --log      Tail the log file"
        echo "  --help     Show this help"
        echo ""
        ;;
    *)
        start_with_manager
        ;;
esac
