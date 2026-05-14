#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# BABSHARQII v40.0 "مأمون" — Neural HUD Dashboard Startup Script
# يبدأ الباك إند (FastAPI) والفرونت إند (Next.js) مع فحوصات الصحة
# 5 Brains × 3 Providers × 162 Features × 26 Sections × 12 Layers
#
# Usage:
#   ./start-dashboard.sh                # Start everything
#   ./start-dashboard.sh backend        # Backend only
#   ./start-dashboard.sh frontend       # Frontend only
#   ./start-dashboard.sh build          # Build frontend only
#   ./start-dashboard.sh test           # Run comprehensive tests
#   ./start-dashboard.sh full-test      # Full test + API + Frontend
#   ./start-dashboard.sh stop           # Stop all services
#   ./start-dashboard.sh status         # Show service status
#   ./start-dashboard.sh check          # Pre-flight checks
#   ./start-dashboard.sh dev            # Dev mode with auto-reload
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ─── Design Palette ───────────────────────────────────────────────────────────
BLACK='\033[0;30m'
SILVER='\033[0;37m'    # #C8CED6
ION_BLUE='\033[0;34m'  # #4A9EFF
GRAY='\033[0;90m'      # #5A6270
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
LOG_DIR="$SCRIPT_DIR/.logs"
PID_DIR="$SCRIPT_DIR/.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

mkdir -p "$LOG_DIR" "$PID_DIR" "$BACKEND_DIR/data" "$BACKEND_DIR/logs" "$BACKEND_DIR/sandbox" "$BACKEND_DIR/backups"

cd "$SCRIPT_DIR"

# ─── Banner ───────────────────────────────────────────────────────────────────

echo ""
echo -e "${ION_BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${ION_BLUE}║${NC}  ${BOLD}BABSHARQII v40.0 — مأمون — Neural HUD Dashboard${NC}            ${ION_BLUE}║${NC}"
echo -e "${ION_BLUE}║${NC}  ${SILVER}5 Brains · 3 Providers · 162 Features · 26 Sections${NC}      ${ION_BLUE}║${NC}"
echo -e "${ION_BLUE}║${NC}  ${SILVER}12 Layers · NeuralBus · GlobalWorkspace · Living Systems${NC} ${ION_BLUE}║${NC}"
echo -e "${ION_BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Utility Functions ────────────────────────────────────────────────────────

log_step()    { echo -e "  ${ION_BLUE}[→]${NC} $1"; }
log_ok()      { echo -e "  ${GREEN}[✓]${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}[!]${NC} $1"; }
log_err()     { echo -e "  ${RED}[✗]${NC} $1"; }

is_pid_alive() {
    [ -n "$1" ] && kill -0 "$1" 2>/dev/null
}

read_pid() {
    if [ -f "$1" ]; then
        local pid=$(cat "$1" 2>/dev/null)
        if [ -n "$pid" ] && is_pid_alive "$pid"; then
            echo "$pid"
            return 0
        else
            rm -f "$1"
        fi
    fi
    return 1
}

# ─── Pre-flight Check ────────────────────────────────────────────────────────

preflight_check() {
    echo -e "${BOLD}  ═══ Pre-flight Check ═══${NC}"
    echo ""
    
    local ok=true
    
    # Python
    if command -v python3 &>/dev/null; then
        PY_VER=$(python3 --version 2>&1 | head -1)
        log_ok "Python: $PY_VER"
    else
        log_err "Python3 not found"
        ok=false
    fi
    
    # Node.js
    if command -v node &>/dev/null; then
        NODE_VER=$(node --version 2>&1)
        log_ok "Node.js: $NODE_VER"
    else
        log_err "Node.js not found"
        ok=false
    fi
    
    # FastAPI
    if python3 -c "import fastapi" 2>/dev/null; then
        log_ok "FastAPI installed"
    else
        log_err "FastAPI not installed — run: pip3 install -r backend/requirements.txt"
        ok=false
    fi
    
    # laws.yaml
    if [ -f "$BACKEND_DIR/laws.yaml" ]; then
        log_ok "laws.yaml: present"
    else
        log_err "laws.yaml: MISSING — CRITICAL safety file"
        ok=false
    fi
    
    # .env
    if [ -f "$BACKEND_DIR/.env" ] || [ -f "$SCRIPT_DIR/.env" ]; then
        log_ok ".env: present"
    else
        log_warn ".env: not found (will use defaults)"
    fi
    
    # 12 Layer check
    echo ""
    log_step "12-Layer Verification:"
    local layer_files=(
        "mamoun/api/update.py|Layer1-ProjectOrchestrator"
        "mamoun/core/self_healing.py|Layer2-SelfHealing"
        "mamoun/core/consciousness_loop.py|Layer3-ConsciousnessLoop"
        "mamoun/physical/blender_controller.py|Layer4-BlenderController"
        "mamoun/evolution/self_evolution_scheduler.py|Layer5-EvolutionScheduler"
        "mamoun/core/mamoun_kernel.py|Layer6-MamounKernel"
        "mamoun/core/neural_bus.py|Layer7-NeuralBus"
        "mamoun/core/skill_executor.py|Layer8-SkillExecutor"
        "mamoun/core/project_registry.py|Layer9-ProjectRegistry"
        "mamoun/core/smart_scheduler.py|Layer10-SmartScheduler"
        "mamoun/core/project_pool.py|Layer11-ProjectPool"
        "mamoun/core/session_context.py|Layer12-SessionContext"
    )
    
    local layers_ok=0
    for entry in "${layer_files[@]}"; do
        IFS='|' read -r file name <<< "$entry"
        if [ -f "$BACKEND_DIR/$file" ]; then
            log_ok "$name"
            layers_ok=$((layers_ok + 1))
        else
            log_err "$name — $file MISSING"
            ok=false
        fi
    done
    
    echo ""
    if [ $layers_ok -eq 12 ]; then
        log_ok "All 12 layers present ✓"
    else
        log_err "Only $layers_ok/12 layers found"
    fi
    
    echo ""
    if $ok; then
        log_ok "Pre-flight check: ALL CLEAR"
        return 0
    else
        log_err "Pre-flight check: ISSUES FOUND — fix before proceeding"
        return 1
    fi
}

# ─── Check Dependencies ──────────────────────────────────────────────────────

check_deps() {
    log_step "[1/6] Checking dependencies..."
    
    if [ ! -d "node_modules" ]; then
        echo -e "  ${SILVER}Installing frontend dependencies...${NC}"
        npm install --legacy-peer-deps 2>&1 | tail -3
    else
        log_ok "node_modules present"
    fi
    
    if [ -f "backend/requirements.txt" ]; then
        if ! python3 -c "import fastapi" 2>/dev/null; then
            echo -e "  ${SILVER}Installing backend dependencies...${NC}"
            pip3 install -r backend/requirements.txt 2>&1 | tail -3
        else
            log_ok "Python dependencies present"
        fi
    fi
    
    log_ok "Dependencies ready"
}

# ─── Build Frontend ──────────────────────────────────────────────────────────

build_frontend() {
    log_step "[2/6] Building frontend..."
    
    if [ ! -d ".next/server/app" ]; then
        echo -e "  ${SILVER}Running Next.js build...${NC}"
        npx next build 2>&1 | tail -5 || {
            log_warn "Next.js build failed — running in dev mode instead"
        }
    else
        log_ok "Build already exists (run 'npm run build' to rebuild)"
    fi
}

# ─── Load Environment ────────────────────────────────────────────────────────

load_env() {
    log_step "[3/6] Loading environment..."
    
    if [ -f "$SCRIPT_DIR/.env" ]; then
        set -a
        source "$SCRIPT_DIR/.env" 2>/dev/null || true
        set +a
        log_ok ".env loaded"
    elif [ -f "$BACKEND_DIR/.env" ]; then
        set -a
        source "$BACKEND_DIR/.env" 2>/dev/null || true
        set +a
        log_ok "backend/.env loaded"
    else
        log_warn "No .env file found — using defaults"
    fi
    
    export MAMOUN_BACKEND_URL="${MAMOUN_BACKEND_URL:-http://localhost:8000}"
    export MAMOUN_FRONTEND_URL="${MAMOUN_FRONTEND_URL:-http://localhost:3000}"
    export PORT="${PORT:-3000}"
}

# ─── Start Backend ───────────────────────────────────────────────────────────

start_backend() {
    log_step "[4/6] Starting backend (FastAPI on :8000)..."
    
    # Check if already running
    local existing_pid
    existing_pid=$(read_pid "$BACKEND_PID_FILE" || true)
    if [ -n "$existing_pid" ]; then
        if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
            log_ok "Backend already running (PID: $existing_pid)"
            return
        else
            log_warn "Stale backend PID — restarting"
            rm -f "$BACKEND_PID_FILE"
        fi
    elif curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
        log_ok "Backend already running (external)"
        return
    fi
    
    cd "$BACKEND_DIR"
    python3 -m uvicorn mamoun.main:app --host 0.0.0.0 --port 8000 --reload >> "$BACKEND_LOG" 2>&1 &
    local be_pid=$!
    echo "$be_pid" > "$BACKEND_PID_FILE"
    cd "$SCRIPT_DIR"
    
    # Wait for backend to be ready
    log_step "Waiting for backend to start..."
    for i in $(seq 1 30); do
        if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
            # Report brain status
            local brain_info
            brain_info=$(curl -s "http://localhost:8000/health" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    brains = d.get('brains', {})
    print(f'{len(brains)} brains active')
except:
    print('?')
" 2>/dev/null || echo "?")
            log_ok "Backend started on :8000 (PID: $be_pid) — $brain_info"
            return
        fi
        sleep 1
    done
    log_warn "Backend startup timeout — check $BACKEND_LOG"
}

# ─── Start Frontend ──────────────────────────────────────────────────────────

start_frontend() {
    log_step "[5/6] Starting frontend (Next.js on :$PORT)..."
    
    # Check if already running
    local existing_pid
    existing_pid=$(read_pid "$FRONTEND_PID_FILE" || true)
    if [ -n "$existing_pid" ]; then
        if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
            log_ok "Frontend already running (PID: $existing_pid)"
            return
        else
            log_warn "Stale frontend PID — restarting"
            rm -f "$FRONTEND_PID_FILE"
        fi
    fi
    
    npx next dev -p "$PORT" >> "$FRONTEND_LOG" 2>&1 &
    local fe_pid=$!
    echo "$fe_pid" > "$FRONTEND_PID_FILE"
    
    log_step "Waiting for frontend to start..."
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
            log_ok "Frontend started on :$PORT (PID: $fe_pid)"
            return
        fi
        sleep 1
    done
    log_warn "Frontend startup timeout — check $FRONTEND_LOG"
}

# ─── Health Check ────────────────────────────────────────────────────────────

health_check() {
    log_step "[6/6] Running health checks..."
    echo ""
    
    # Frontend
    if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
        log_ok "Frontend: ONLINE (http://localhost:$PORT)"
    else
        log_err "Frontend: OFFLINE"
    fi
    
    # Backend
    if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
        local health_info
        health_info=$(curl -s "http://localhost:8000/health" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    brains = d.get('brains', {})
    kernel = d.get('kernel_running', False)
    winner = d.get('workspace_winner', 'none')
    print(f'{len(brains)} brains | kernel={\"ON\" if kernel else \"OFF\"} | workspace_winner={winner}')
except:
    print('parse error')
" 2>/dev/null || echo "parse error")
        log_ok "Backend:  ONLINE (http://localhost:8000) — $health_info"
    else
        log_warn "Backend:  OFFLINE — Dashboard runs in standalone mode"
    fi
    
    echo ""
    echo -e "${ION_BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ${BOLD}MAMOUN Neural HUD Dashboard is running!${NC}"
    echo -e "${SILVER}  Dashboard:  http://localhost:$PORT${NC}"
    echo -e "${SILVER}  Backend:    http://localhost:8000${NC}"
    echo -e "${SILVER}  API Docs:   http://localhost:8000/docs${NC}"
    echo -e "${SILVER}  Health:     http://localhost:8000/health${NC}"
    echo -e "${SILVER}  Metrics:    http://localhost:8000/metrics${NC}"
    echo -e "${GRAY}  Logs:       $LOG_DIR/${NC}"
    echo -e "${GRAY}  Stop:       ./start-dashboard.sh stop${NC}"
    echo -e "${ION_BLUE}══════════════════════════════════════════════════════════════${NC}"
}

# ─── Stop Services ───────────────────────────────────────────────────────────

stop_services() {
    echo -e "  ${SILVER}Stopping services...${NC}"
    
    # Stop backend
    local be_pid
    be_pid=$(read_pid "$BACKEND_PID_FILE" || true)
    if [ -n "$be_pid" ]; then
        kill "$be_pid" 2>/dev/null || true
        sleep 1
        if is_pid_alive "$be_pid"; then
            kill -9 "$be_pid" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
        log_ok "Backend stopped (Law 5: no shutdown resistance)"
    fi
    
    # Stop frontend
    local fe_pid
    fe_pid=$(read_pid "$FRONTEND_PID_FILE" || true)
    if [ -n "$fe_pid" ]; then
        kill "$fe_pid" 2>/dev/null || true
        sleep 1
        if is_pid_alive "$fe_pid"; then
            kill -9 "$fe_pid" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
        log_ok "Frontend stopped"
    fi
    
    # Kill orphans
    pkill -f "uvicorn mamoun.main:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    
    log_ok "All services stopped"
}

# ─── Show Status ─────────────────────────────────────────────────────────────

show_status() {
    echo -e "${BOLD}  Service Status:${NC}"
    echo ""
    
    # Backend
    if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
        local health
        health=$(curl -s "http://localhost:8000/health" 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "parse error")
        log_ok "Backend: ONLINE"
        echo "$health" | head -20
    else
        log_err "Backend: OFFLINE"
    fi
    
    echo ""
    
    # Frontend
    if curl -s "http://localhost:${PORT:-3000}" > /dev/null 2>&1; then
        log_ok "Frontend: ONLINE (http://localhost:${PORT:-3000})"
    else
        log_err "Frontend: OFFLINE"
    fi
    
    echo ""
    
    # PIDs
    local be_pid fe_pid
    be_pid=$(read_pid "$BACKEND_PID_FILE" 2>/dev/null || echo "none")
    fe_pid=$(read_pid "$FRONTEND_PID_FILE" 2>/dev/null || echo "none")
    echo -e "  ${SILVER}Backend PID:  $be_pid${NC}"
    echo -e "  ${SILVER}Frontend PID: $fe_pid${NC}"
}

# ─── Run Tests ───────────────────────────────────────────────────────────────

run_tests() {
    echo -e "${BOLD}  Running Comprehensive Tests...${NC}"
    echo ""
    
    if [ -f "$SCRIPT_DIR/mamoun-comprehensive-test.sh" ]; then
        bash "$SCRIPT_DIR/mamoun-comprehensive-test.sh" "$@"
    elif [ -f "$SCRIPT_DIR/12-LAYER-TEST.sh" ]; then
        bash "$SCRIPT_DIR/12-LAYER-TEST.sh" "$@"
    else
        # Fallback to pytest
        cd "$BACKEND_DIR"
        MAMOUN_LLM_API_URL=http://localhost:9999 MAMOUN_AUTO_EVOLVE=false \
            python3 -m pytest tests/test_mamoun_comprehensive_v35.py -v --tb=short
    fi
}

# ─── Parse Arguments ─────────────────────────────────────────────────────────

case "${1:-all}" in
    check)
        preflight_check
        ;;
    backend)
        load_env
        cd "$BACKEND_DIR"
        exec python3 -m uvicorn mamoun.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    frontend)
        load_env
        exec npx next dev -p "${PORT:-3000}"
        ;;
    build)
        check_deps
        build_frontend
        log_ok "Build complete"
        ;;
    test)
        shift || true
        run_tests "$@"
        ;;
    full-test)
        # Start services, then run full tests
        check_deps
        load_env
        start_backend
        sleep 3
        start_frontend
        sleep 3
        run_tests --all
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    dev)
        load_env
        # Start backend with reload
        cd "$BACKEND_DIR"
        python3 -m uvicorn mamoun.main:app --host 0.0.0.0 --port 8000 --reload >> "$BACKEND_LOG" 2>&1 &
        local be_pid=$!
        echo "$be_pid" > "$BACKEND_PID_FILE"
        cd "$SCRIPT_DIR"
        
        # Wait for backend
        log_step "Waiting for backend..."
        for i in $(seq 1 20); do
            if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
                log_ok "Backend ready!"
                break
            fi
            sleep 1
        done
        
        # Start frontend with hot-reload
        npx next dev -p "${PORT:-3000}" 2>&1 | tee dev.log &
        local fe_pid=$!
        echo "$fe_pid" > "$FRONTEND_PID_FILE"
        
        echo ""
        echo -e "${GREEN}  ${BOLD}DEV MODE — Auto-reload ON${NC}"
        echo -e "  ${SILVER}Backend:  http://localhost:8000${NC}"
        echo -e "  ${SILVER}Frontend: http://localhost:${PORT:-3000}${NC}"
        echo -e "  ${GRAY}Press Ctrl+C to stop${NC}"
        echo ""
        
        wait
        ;;
    all|*)
        preflight_check || true
        check_deps
        build_frontend
        load_env
        start_backend
        start_frontend
        health_check
        wait
        ;;
esac
