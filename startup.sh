#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# BABSHARQII v50.0 "مأمون" — Multi-Brain AGI System Startup / Deployment Script
# سكريبت التشغيل والنشر لنظام مأمون متعدد الأدمغة
#
# 5 Brains × 7 Providers × 162 Features × 26 Sections × 12 Layers
# NeuralBus · GlobalWorkspace · Living Systems · ConsciousnessLoop
# Real CodeGen · ProjectScaffolder · ExternalProjectController · CapabilityAssessor
#
# v50.0: 100% CONTROL FUSION — No more MOCK, no more empty templates
# - CodeGenerationEngine: REAL (LLM-connected)
# - AgentCreator: REAL (LLM generates logic)
# - SelfModifier: TypeScript/JS support
# - ProjectScaffolder: Build projects from scratch
# - ExternalProjectController: Full external project control
# - AutoResearchHealLoop: Auto-trigger enabled
#
# Usage / الاستخدام:
#   ./startup.sh start              # Start all services (dev mode) / تشغيل كل الخدمات
#   ./startup.sh start --prod       # Start all services (production) / تشغيل بالإنتاج
#   ./startup.sh stop               # Stop all services / إيقاف كل الخدمات
#   ./startup.sh restart            # Restart all services / إعادة التشغيل
#   ./startup.sh restart --prod     # Restart in production mode / إعادة تشغيل بالإنتاج
#   ./startup.sh status             # Show service status / عرض حالة الخدمات
#   ./startup.sh build              # Build frontend for production / بناء الواجهة
#   ./startup.sh test               # Run comprehensive tests / تشغيل الاختبارات
#   ./startup.sh pm2                # Generate PM2 config & start production / تشغيل بـ PM2
#   ./startup.sh health             # Run health checks / فحص الصحة
#   ./startup.sh api-test           # Test API endpoints / اختبار نقاط الاتصال
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Color Palette / لوحة الألوان ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
SILVER='\033[0;37m'
GRAY='\033[0;90m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ─── Paths / المسارات ────────────────────────────────────────────────────────────────────────────
PROJECT_DIR="/home/z/babsharqii-v5"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR"
VENV_DIR="$BACKEND_DIR/venv"
LOG_DIR="$PROJECT_DIR/.logs"
PID_DIR="$PROJECT_DIR/.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
ECOSYSTEM_FILE="$PROJECT_DIR/ecosystem.config.js"

# ─── Ports / المنافذ ─────────────────────────────────────────────────────────────────────────────
BACKEND_PORT=8000
DEV_PORT=3000
PROD_PORT=4000

# ─── Mode / الوضع ─────────────────────────────────────────────────────────────────────────────────
MODE="dev"

# ─── Create dirs / إنشاء المجلدات ────────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$PID_DIR" "$BACKEND_DIR/data" "$BACKEND_DIR/logs" "$BACKEND_DIR/sandbox" "$BACKEND_DIR/backups"

cd "$PROJECT_DIR"

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Banner / الشعار
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

show_banner() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${BOLD}BABSHARQII v50.0 — مأمون — Multi-Brain AGI System${NC}                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${SILVER}5 أدمغة · 3 مزودين · 162 ميزة · 26 قسم · 12 طبقة${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}v50.0 FUSION: Real CodeGen · ProjectScaffolder · ExternalCtrl${NC}    ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${SILVER}NeuralBus · GlobalWorkspace · Living Systems · ConsciousnessLoop${NC}  ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Logging / التسجيل
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

log_step()    { echo -e "  ${BLUE}[→]${NC} $1 ${DIM}$2${NC}"; }
log_ok()      { echo -e "  ${GREEN}[✓]${NC} $1 ${DIM}$2${NC}"; }
log_warn()    { echo -e "  ${YELLOW}[!]${NC} $1 ${DIM}$2${NC}"; }
log_err()     { echo -e "  ${RED}[✗]${NC} $1 ${DIM}$2${NC}"; }
log_info()    { echo -e "  ${CYAN}[i]${NC} $1 ${DIM}$2${NC}"; }

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# PID Management / إدارة معرفات العمليات
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

is_pid_alive() {
    [ -n "$1" ] && kill -0 "$1" 2>/dev/null
}

read_pid() {
    if [ -f "$1" ]; then
        local pid
        pid=$(cat "$1" 2>/dev/null)
        if [ -n "$pid" ] && is_pid_alive "$pid"; then
            echo "$pid"
            return 0
        else
            rm -f "$1"
        fi
    fi
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Environment Loading / تحميل البيئة
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

load_env() {
    log_step "تحميل متغيرات البيئة / Loading environment..."

    if [ -f "$PROJECT_DIR/.env" ]; then
        set -a
        source "$PROJECT_DIR/.env" 2>/dev/null || true
        set +a
        log_ok ".env loaded from project root"
    elif [ -f "$BACKEND_DIR/.env" ]; then
        set -a
        source "$BACKEND_DIR/.env" 2>/dev/null || true
        set +a
        log_ok ".env loaded from backend dir"
    else
        log_warn "لم يتم العثور على .env / No .env file found — using defaults"
    fi

    export MAMOUN_BACKEND_URL="${MAMOUN_BACKEND_URL:-http://localhost:${BACKEND_PORT}}"
    export MAMOUN_FRONTEND_URL="${MAMOUN_FRONTEND_URL:-http://localhost:${DEV_PORT}}"

    if [ "$MODE" = "prod" ]; then
        export PORT="${PORT:-${PROD_PORT}}"
    else
        export PORT="${PORT:-${DEV_PORT}}"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Python Virtual Environment / البيئة الافتراضية لبايثون
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

setup_venv() {
    log_step "فحص البيئة الافتراضية / Checking Python venv..."

    # Check if venv exists and is valid
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python3" ] && [ -f "$VENV_DIR/bin/pip3" ]; then
        local py_ver
        py_ver=$("$VENV_DIR/bin/python3" --version 2>&1 | head -1)
        log_ok "البيئة الافتراضية موجودة / Venv exists: $py_ver"

        # Verify critical dependencies are importable
        if ! "$VENV_DIR/bin/python3" -c "import fastapi, uvicorn, pydantic, websockets, httpx" 2>/dev/null; then
            log_warn "بعض المكتبات مفقودة / Some dependencies missing — reinstalling..."
            "$VENV_DIR/bin/pip3" install -r "$BACKEND_DIR/requirements.txt" --quiet 2>&1 | tail -3
            log_ok "تم تثبيت المكتبات / Dependencies reinstalled"
        fi
        return 0
    fi

    # Recreate venv
    log_step "إنشاء البيئة الافتراضية / Creating Python venv..."

    if ! command -v python3 &>/dev/null; then
        log_err "python3 غير مثبت / python3 not found!"
        log_err "يرجى تثبيت Python 3.10+ / Please install Python 3.10+"
        exit 1
    fi

    local py_ver
    py_ver=$(python3 --version 2>&1 | head -1)
    log_info "Using: $py_ver"

    # Remove old/broken venv
    if [ -d "$VENV_DIR" ]; then
        log_warn "حذف البيئة القديمة / Removing broken venv..."
        rm -rf "$VENV_DIR"
    fi

    # Create new venv
    python3 -m venv "$VENV_DIR" 2>&1 || {
        log_err "فشل إنشاء البيئة الافتراضية / Failed to create venv"
        exit 1
    }
    log_ok "تم إنشاء البيئة الافتراضية / Venv created"

    # Upgrade pip
    "$VENV_DIR/bin/python3" -m pip install --upgrade pip --quiet 2>&1 | tail -1

    # Install dependencies
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        log_step "تثبيت المكتبات / Installing Python dependencies..."
        "$VENV_DIR/bin/pip3" install -r "$BACKEND_DIR/requirements.txt" 2>&1 | tail -5
        log_ok "تم تثبيت المكتبات / Python dependencies installed"
    else
        log_err "ملف المتطلبات غير موجود / requirements.txt not found at $BACKEND_DIR/requirements.txt"
        exit 1
    fi

    # Verify critical imports
    log_step "التحقق من المكتبات / Verifying critical imports..."
    local critical_ok=true
    for pkg in fastapi uvicorn pydantic websockets httpx; do
        if "$VENV_DIR/bin/python3" -c "import $pkg" 2>/dev/null; then
            log_ok "$pkg ✓"
        else
            log_err "$pkg — فشل الاستيراد / import failed"
            critical_ok=false
        fi
    done

    if ! $critical_ok; then
        log_err "بعض المكتبات الأساسية فشلت / Critical imports failed"
        exit 1
    fi

    log_ok "البيئة الافتراضية جاهزة / Venv ready ✓"
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Frontend Dependencies / مكتبات الواجهة الأمامية
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

setup_frontend_deps() {
    log_step "فحص مكتبات الواجهة / Checking frontend dependencies..."

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        log_step "تثبيت مكتبات الواجهة / Installing frontend dependencies..."
        cd "$FRONTEND_DIR"
        npm install --legacy-peer-deps 2>&1 | tail -5
        log_ok "تم تثبيت مكتبات الواجهة / Frontend dependencies installed"
    else
        log_ok "مكتبات الواجهة موجودة / node_modules present"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Build Frontend / بناء الواجهة الأمامية
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

build_frontend() {
    log_step "بناء الواجهة الأمامية / Building Next.js frontend..."

    cd "$FRONTEND_DIR"
    setup_frontend_deps

    npx next build 2>&1 | tail -10 || {
        log_err "فشل البناء / Next.js build failed"
        exit 1
    }
    log_ok "اكتمل البناء / Build complete"

    # Copy static files to standalone output
    log_step "نسخ الملفات الثابتة / Copying static files to standalone output..."

    if [ -d "$FRONTEND_DIR/.next/standalone" ]; then
        # Copy .next/static to standalone/.next/static
        if [ -d "$FRONTEND_DIR/.next/static" ]; then
            cp -r "$FRONTEND_DIR/.next/static" "$FRONTEND_DIR/.next/standalone/.next/static"
            log_ok "تم نسخ .next/static / .next/static copied"
        else
            log_warn ".next/static غير موجود / .next/static not found"
        fi

        # Copy public to standalone/public
        if [ -d "$FRONTEND_DIR/public" ]; then
            cp -r "$FRONTEND_DIR/public" "$FRONTEND_DIR/.next/standalone/public"
            log_ok "تم نسخ public / public copied"
        else
            log_warn "public غير موجود / public dir not found"
        fi

        log_ok "تم نسخ جميع الملفات الثابتة / All static files copied to standalone"
    else
        log_err "مجلد standalone غير موجود / .next/standalone not found — build may have failed"
        exit 1
    fi

    log_ok "البناء مكتمل والملفات جاهزة / Build complete and files ready for production"
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Start Backend / تشغيل الباك إند
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

start_backend() {
    log_step "تشغيل الباك إند / Starting backend (FastAPI on :${BACKEND_PORT})..."

    # Check if already running
    local existing_pid
    existing_pid=$(read_pid "$BACKEND_PID_FILE" || true)
    if [ -n "$existing_pid" ]; then
        if curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
            log_ok "الباك إند يعمل بالفعل / Backend already running (PID: $existing_pid)"
            return 0
        else
            log_warn "عملية قديمة / Stale backend PID — restarting"
            rm -f "$BACKEND_PID_FILE"
        fi
    elif curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
        log_ok "الباك إند يعمل / Backend already running (external process)"
        return 0
    fi

    # Ensure venv is set up
    setup_venv

    # Start backend using venv's uvicorn
    cd "$BACKEND_DIR"

    if [ "$MODE" = "prod" ]; then
        "$VENV_DIR/bin/python3" -m uvicorn mamoun.main:app \
            --host 0.0.0.0 \
            --port "$BACKEND_PORT" \
            --workers 2 \
            >> "$BACKEND_LOG" 2>&1 &
    else
        "$VENV_DIR/bin/python3" -m uvicorn mamoun.main:app \
            --host 0.0.0.0 \
            --port "$BACKEND_PORT" \
            --reload \
            >> "$BACKEND_LOG" 2>&1 &
    fi

    local be_pid=$!
    echo "$be_pid" > "$BACKEND_PID_FILE"
    cd "$PROJECT_DIR"

    # Wait for backend to be ready
    log_step "انتظار الباك إند / Waiting for backend to start..."
    local attempts=0
    local max_attempts=45
    while [ $attempts -lt $max_attempts ]; do
        if curl -sf "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
            # Parse brain info from health endpoint
            local brain_info
            brain_info=$(curl -sf "http://localhost:${BACKEND_PORT}/health" 2>/dev/null | \
                "$VENV_DIR/bin/python3" -c "
import json, sys
try:
    d = json.load(sys.stdin)
    brains = d.get('brains', {})
    kernel = d.get('kernel_running', False)
    winner = d.get('workspace_winner', 'none')
    print(f'{len(brains)} brains active | kernel={\"ON\" if kernel else \"OFF\"} | workspace_winner={winner}')
except:
    print('response received')
" 2>/dev/null || echo "response received")
            log_ok "تم تشغيل الباك إند / Backend started on :${BACKEND_PORT} (PID: $be_pid) — $brain_info"
            return 0
        fi

        # Check if process died
        if ! is_pid_alive "$be_pid"; then
            log_err "الباك إند توقف / Backend process died — check $BACKEND_LOG"
            tail -20 "$BACKEND_LOG" 2>/dev/null
            exit 1
        fi

        sleep 1
        attempts=$((attempts + 1))
        if [ $((attempts % 10)) -eq 0 ]; then
            log_info "لا يزال قيد الانتظار... / Still waiting... ($attempts/${max_attempts}s)"
        fi
    done

    log_warn "انتهت مهلة تشغيل الباك إند / Backend startup timeout — check $BACKEND_LOG"
    log_info "آخر السجلات / Recent logs:"
    tail -10 "$BACKEND_LOG" 2>/dev/null
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Start Frontend / تشغيل الواجهة الأمامية
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

start_frontend() {
    local fe_port="$PORT"

    if [ "$MODE" = "prod" ]; then
        log_step "تشغيل الواجهة بالإنتاج / Starting frontend (Production on :${fe_port})..."

        # Verify standalone build exists
        if [ ! -f "$FRONTEND_DIR/.next/standalone/server.js" ]; then
            log_err "البناء غير موجود / Standalone build not found — run './startup.sh build' first"
            exit 1
        fi
    else
        log_step "تشغيل الواجهة بالتطوير / Starting frontend (Dev on :${fe_port})..."
        setup_frontend_deps
    fi

    # Check if already running
    local existing_pid
    existing_pid=$(read_pid "$FRONTEND_PID_FILE" || true)
    if [ -n "$existing_pid" ]; then
        if curl -sf "http://localhost:${fe_port}" > /dev/null 2>&1; then
            log_ok "الواجهة تعمل بالفعل / Frontend already running (PID: $existing_pid)"
            return 0
        else
            log_warn "عملية قديمة / Stale frontend PID — restarting"
            rm -f "$FRONTEND_PID_FILE"
        fi
    elif curl -sf "http://localhost:${fe_port}" > /dev/null 2>&1; then
        log_ok "الواجهة تعمل / Frontend already running (external process)"
        return 0
    fi

    cd "$FRONTEND_DIR"

    if [ "$MODE" = "prod" ]; then
        # Production: use standalone server
        PORT="$fe_port" node .next/standalone/server.js >> "$FRONTEND_LOG" 2>&1 &
    else
        # Development: use next dev
        npx next dev -p "$fe_port" >> "$FRONTEND_LOG" 2>&1 &
    fi

    local fe_pid=$!
    echo "$fe_pid" > "$FRONTEND_PID_FILE"
    cd "$PROJECT_DIR"

    # Wait for frontend to be ready
    log_step "انتظار الواجهة / Waiting for frontend to start..."
    local attempts=0
    local max_attempts=60
    while [ $attempts -lt $max_attempts ]; do
        if curl -sf "http://localhost:${fe_port}" > /dev/null 2>&1; then
            log_ok "تم تشغيل الواجهة / Frontend started on :${fe_port} (PID: $fe_pid)"
            return 0
        fi

        # Check if process died
        if ! is_pid_alive "$fe_pid"; then
            log_err "الواجهة توقفت / Frontend process died — check $FRONTEND_LOG"
            tail -20 "$FRONTEND_LOG" 2>/dev/null
            exit 1
        fi

        sleep 1
        attempts=$((attempts + 1))
        if [ $((attempts % 15)) -eq 0 ]; then
            log_info "لا يزال قيد الانتظار... / Still waiting... ($attempts/${max_attempts}s)"
        fi
    done

    log_warn "انتهت مهلة تشغيل الواجهة / Frontend startup timeout — check $FRONTEND_LOG"
    log_info "آخر السجلات / Recent logs:"
    tail -10 "$FRONTEND_LOG" 2>/dev/null
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Stop Services / إيقاف الخدمات
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

stop_services() {
    echo -e "  ${SILVER}إيقاف الخدمات / Stopping services...${NC}"

    # Stop backend
    local be_pid
    be_pid=$(read_pid "$BACKEND_PID_FILE" || true)
    if [ -n "$be_pid" ]; then
        kill "$be_pid" 2>/dev/null || true
        sleep 2
        if is_pid_alive "$be_pid"; then
            log_warn "القوة الإيقاف / Force-killing backend..."
            kill -9 "$be_pid" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
        log_ok "تم إيقاف الباك إند / Backend stopped (Law 5: no shutdown resistance)"
    fi

    # Stop frontend
    local fe_pid
    fe_pid=$(read_pid "$FRONTEND_PID_FILE" || true)
    if [ -n "$fe_pid" ]; then
        kill "$fe_pid" 2>/dev/null || true
        sleep 2
        if is_pid_alive "$fe_pid"; then
            log_warn "القوة الإيقاف / Force-killing frontend..."
            kill -9 "$fe_pid" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
        log_ok "تم إيقاف الواجهة / Frontend stopped"
    fi

    # Kill any orphan processes
    pkill -f "uvicorn mamoun.main:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next start" 2>/dev/null || true
    pkill -f ".next/standalone/server.js" 2>/dev/null || true

    log_ok "تم إيقاف جميع الخدمات / All services stopped"
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Health Checks / فحوصات الصحة
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

run_health_checks() {
    echo ""
    echo -e "${BOLD}  ═══ فحص الصحة / Health Checks ═══${NC}"
    echo ""

    local all_healthy=true

    # ── Backend Health / صحة الباك إند ─────────────────────────────────────────
    echo -e "  ${CYAN}── الباك إند / Backend ──${NC}"

    if curl -sf --max-time 5 "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
        local health_raw
        health_raw=$(curl -sf --max-time 5 "http://localhost:${BACKEND_PORT}/health" 2>/dev/null || echo "{}")

        local health_info
        health_info=$(echo "$health_raw" | "$VENV_DIR/bin/python3" -c "
import json, sys
try:
    d = json.load(sys.stdin)
    status = d.get('status', 'unknown')
    version = d.get('version', '?')
    brains = d.get('brains', {})
    kernel = d.get('kernel_running', False)
    winner = d.get('workspace_winner', 'none')
    brain_names = ', '.join(brains.keys()) if brains else 'none'
    print(f'status={status} | v{version} | brains: {len(brains)} [{brain_names}] | kernel={\"ON\" if kernel else \"OFF\"} | workspace_winner={winner}')
except Exception as e:
    print(f'parse error: {e}')
" 2>/dev/null || echo "parse error")

        log_ok "الباك إند يعمل / Backend: ONLINE (http://localhost:${BACKEND_PORT})"
        echo -e "    ${SILVER}$health_info${NC}"
    else
        log_err "الباك إند متوقف / Backend: OFFLINE"
        all_healthy=false
    fi

    echo ""

    # ── Frontend Health / صحة الواجهة ─────────────────────────────────────────
    echo -e "  ${CYAN}── الواجهة الأمامية / Frontend ──${NC}"

    local fe_port="$PORT"
    if curl -sf --max-time 5 "http://localhost:${fe_port}" > /dev/null 2>&1; then
        local http_code
        http_code=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" "http://localhost:${fe_port}" 2>/dev/null || echo "000")
        log_ok "الواجهة تعمل / Frontend: ONLINE (http://localhost:${fe_port}) [HTTP $http_code]"
    else
        log_err "الواجهة متوقفة / Frontend: OFFLINE"
        all_healthy=false
    fi

    echo ""

    # ── System Resources / موارد النظام ───────────────────────────────────────
    echo -e "  ${CYAN}── موارد النظام / System Resources ──${NC}"

    if command -v free &>/dev/null; then
        local mem_info
        mem_info=$(free -h 2>/dev/null | head -2 | tail -1 | awk '{print "used="$3" / total="$2}')
        log_info "الذاكرة / Memory: $mem_info"
    fi

    local disk_info
    disk_info=$(df -h "$PROJECT_DIR" 2>/dev/null | tail -1 | awk '{print "used="$3" / total="$2" ("$5")"}')
    log_info "القرص / Disk: $disk_info"

    local be_pid_val fe_pid_val
    be_pid_val=$(read_pid "$BACKEND_PID_FILE" 2>/dev/null || echo "none")
    fe_pid_val=$(read_pid "$FRONTEND_PID_FILE" 2>/dev/null || echo "none")
    log_info "Backend PID: $be_pid_val | Frontend PID: $fe_pid_val"

    echo ""

    if $all_healthy; then
        log_ok "جميع الخدمات تعمل / All services healthy ✓"
    else
        log_warn "بعض الخدمات متوقفة / Some services are offline"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# API Endpoint Testing / اختبار نقاط الاتصال
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

run_api_tests() {
    echo ""
    echo -e "${BOLD}  ═══ اختبار نقاط الاتصال / API Endpoint Tests ═══${NC}"
    echo ""

    local pass=0
    local fail=0
    local total=0

    test_endpoint() {
        local method="$1"
        local url="$2"
        local label="$3"
        local expected_code="${4:-200}"
        total=$((total + 1))

        local http_code
        http_code=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" -X "$method" "$url" 2>/dev/null || echo "000")

        if [ "$http_code" = "$expected_code" ] || [ "$http_code" = "307" ]; then
            log_ok "$label — HTTP $http_code ✓"
            pass=$((pass + 1))
        else
            log_err "$label — HTTP $http_code (expected $expected_code)"
            fail=$((fail + 1))
        fi
    }

    # Core endpoints
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/health"          "/health — الصحة"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/metrics"          "/metrics — المقاييس"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/docs"             "/docs — التوثيق"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/openapi.json"     "/openapi.json — مواصفات API"

    # Brain endpoints
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/brains"       "/api/brains — الأدمغة"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/consciousness" "/api/consciousness — الوعي"

    # Living systems
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/living/vitals"        "/api/living/vitals — العلامات الحيوية"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/living/emotions"       "/api/living/emotions — المشاعر"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/living/heartbeat"      "/api/living/heartbeat — نبض القلب"

    # AGI pillars
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/agi/status"    "/api/agi/status — حالة الذكاء"
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/agi/capabilities" "/api/agi/capabilities — القدرات"

    # Neural Bus
    test_endpoint "GET"  "http://localhost:${BACKEND_PORT}/api/v23/neural-bus" "/api/v23/neural-bus — الناقل العصبي"

    # Frontend
    local fe_port="$PORT"
    test_endpoint "GET"  "http://localhost:${fe_port}"                        "Frontend — الواجهة الأمامية"

    echo ""
    echo -e "  ${BOLD}═══ نتائج الاختبار / Test Results ═══${NC}"
    echo -e "  ${GREEN}نجح / Passed: $pass${NC}"
    echo -e "  ${RED}فشل / Failed: $fail${NC}"
    echo -e "  ${SILVER}المجموع / Total:  $total${NC}"

    if [ $fail -eq 0 ]; then
        log_ok "جميع الاختبارات نجحت / All API tests passed ✓"
    else
        log_warn "$fail اختبار فشل / $fail test(s) failed"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Status Display / عرض الحالة
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

show_status() {
    echo ""
    echo -e "${BOLD}  ═══ حالة الخدمات / Service Status ═══${NC}"
    echo ""

    # Backend
    echo -e "  ${CYAN}── الباك إند / Backend (FastAPI :${BACKEND_PORT}) ──${NC}"
    if curl -sf --max-time 3 "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
        local health_raw
        health_raw=$(curl -sf --max-time 3 "http://localhost:${BACKEND_PORT}/health" 2>/dev/null || echo "{}")

        # Try to pretty-print with venv python, fall back to python3
        local python_cmd="$VENV_DIR/bin/python3"
        [ -x "$python_cmd" ] || python_cmd="python3"

        echo "$health_raw" | "$python_cmd" -m json.tool 2>/dev/null | head -25 || echo "$health_raw" | head -5
        log_ok "الحالة: يعمل / Status: ONLINE"
    else
        log_err "الحالة: متوقف / Status: OFFLINE"
    fi

    echo ""

    # Frontend
    echo -e "  ${CYAN}── الواجهة / Frontend (Next.js :${PORT}) ──${NC}"
    if curl -sf --max-time 3 "http://localhost:${PORT}" > /dev/null 2>&1; then
        log_ok "الحالة: يعمل / Status: ONLINE (http://localhost:${PORT})"
    else
        log_err "الحالة: متوقف / Status: OFFLINE"
    fi

    echo ""

    # PIDs & Mode
    local be_pid_val fe_pid_val
    be_pid_val=$(read_pid "$BACKEND_PID_FILE" 2>/dev/null || echo "none")
    fe_pid_val=$(read_pid "$FRONTEND_PID_FILE" 2>/dev/null || echo "none")
    echo -e "  ${SILVER}Backend PID:   $be_pid_val${NC}"
    echo -e "  ${SILVER}Frontend PID:  $fe_pid_val${NC}"
    echo -e "  ${SILVER}Mode:          $MODE${NC}"
    echo -e "  ${SILVER}Backend Port:  ${BACKEND_PORT}${NC}"
    echo -e "  ${SILVER}Frontend Port: ${PORT}${NC}"
    echo -e "  ${SILVER}Logs:          ${LOG_DIR}/${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Run Tests / تشغيل الاختبارات
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

run_tests() {
    echo ""
    echo -e "${BOLD}  ═══ تشغيل الاختبارات / Running Tests ═══${NC}"
    echo ""

    setup_venv

    # Backend tests with pytest
    log_step "اختبارات الباك إند / Backend tests..."
    cd "$BACKEND_DIR"

    MAMOUN_LLM_API_URL=http://localhost:9999 \
    MAMOUN_AUTO_EVOLVE=false \
    "$VENV_DIR/bin/python3" -m pytest -x --tb=short -q 2>&1 | tail -20 || {
        log_warn "بعض اختبارات الباك إند فشلت / Some backend tests failed"
    }

    cd "$PROJECT_DIR"

    # Frontend tests with vitest
    if [ -f "$FRONTEND_DIR/vitest.config.ts" ] || [ -f "$FRONTEND_DIR/vitest.config.js" ]; then
        log_step "اختبارات الواجهة / Frontend tests..."
        cd "$FRONTEND_DIR"
        npx vitest run 2>&1 | tail -20 || {
            log_warn "بعض اختبارات الواجهة فشلت / Some frontend tests failed"
        }
        cd "$PROJECT_DIR"
    fi

    log_ok "اكتملت الاختبارات / Tests complete"
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# PM2 Ecosystem Config / إعدادات PM2
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

generate_pm2_config() {
    log_step "إنشاء ملف إعدادات PM2 / Generating PM2 ecosystem.config.js..."

    cat > "$ECOSYSTEM_FILE" << 'ECOSYSTEM_EOF'
// ═══════════════════════════════════════════════════════════════════════════════
// BABSHARQII v40.0 "مأمون" — PM2 Ecosystem Configuration
// إعدادات PM2 لنظام مأمون متعدد الأدمغة
// ═══════════════════════════════════════════════════════════════════════════════

module.exports = {
  apps: [
    // ── Backend: FastAPI + Uvicorn ─────────────────────────────────────────────
    {
      name: 'mamoun-backend',
      cwd: '/home/z/babsharqii-v5/backend',
      script: '/home/z/babsharqii-v5/backend/venv/bin/python3',
      args: '-m uvicorn mamoun.main:app --host 0.0.0.0 --port 8000 --workers 2',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      watch: false,
      max_memory_restart: '1G',
      env: {
        MAMOUN_BACKEND_URL: 'http://localhost:8000',
        MAMOUN_FRONTEND_URL: 'http://localhost:4000',
        MAMOUN_AUTO_EVOLVE: 'false',
        PYTHONUNBUFFERED: '1',
      },
      // Health check
      health_check: {
        interval: 15000,
        url: 'http://localhost:8000/health',
      },
      // Logging
      error_file: '/home/z/babsharqii-v5/.logs/backend-error.log',
      out_file: '/home/z/babsharqii-v5/.logs/backend-out.log',
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      time: true,
    },

    // ── Frontend: Next.js Standalone Production Server ─────────────────────────
    {
      name: 'mamoun-frontend',
      cwd: '/home/z/babsharqii-v5',
      script: '.next/standalone/server.js',
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      watch: false,
      max_memory_restart: '512M',
      env: {
        PORT: '4000',
        HOSTNAME: '0.0.0.0',
        MAMOUN_BACKEND_URL: 'http://localhost:8000',
        MAMOUN_FRONTEND_URL: 'http://localhost:4000',
        NODE_ENV: 'production',
      },
      // Health check
      health_check: {
        interval: 15000,
        url: 'http://localhost:4000',
      },
      // Logging
      error_file: '/home/z/babsharqii-v5/.logs/frontend-error.log',
      out_file: '/home/z/babsharqii-v5/.logs/frontend-out.log',
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      time: true,
    },
  ],

  // ── Deployment Configuration ────────────────────────────────────────────────
  deploy: {
    production: {
      user: 'z',
      host: 'localhost',
      ref: 'origin/main',
      repo: '.',
      path: '/home/z/babsharqii-v5',
      'pre-deploy-local': '',
      'post-deploy': 'npm install --legacy-peer-deps && npm run build && cp -r .next/static .next/standalone/.next/static && cp -r public .next/standalone/public && cd backend && python3 -m venv venv && ./venv/bin/pip3 install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': '',
    },
  },
};
ECOSYSTEM_EOF

    log_ok "تم إنشاء ملف إعدادات PM2 / PM2 ecosystem.config.js generated"
}

start_pm2() {
    log_step "التشغيل بـ PM2 / Starting with PM2..."

    # Ensure venv and build exist
    setup_venv

    if [ ! -f "$FRONTEND_DIR/.next/standalone/server.js" ]; then
        log_warn "البناء غير موجود، جاري البناء... / Build not found, building..."
        build_frontend
    fi

    # Generate config if missing
    if [ ! -f "$ECOSYSTEM_FILE" ]; then
        generate_pm2_config
    fi

    # Check if PM2 is installed
    if ! command -v pm2 &>/dev/null; then
        log_err "PM2 غير مثبت / PM2 not installed — installing..."
        npm install -g pm2 2>&1 | tail -3
    fi

    cd "$PROJECT_DIR"

    # Stop existing PM2 processes if any
    pm2 delete mamoun-backend 2>/dev/null || true
    pm2 delete mamoun-frontend 2>/dev/null || true

    # Start with PM2
    pm2 start "$ECOSYSTEM_FILE" 2>&1 | tail -10

    # Save PM2 process list for auto-restart
    pm2 save 2>/dev/null || true

    echo ""
    pm2 status

    echo ""
    log_ok "تم التشغيل بـ PM2 / PM2 started ✓"
    echo -e "  ${SILVER}التحكم / Control: pm2 status | pm2 logs | pm2 restart all | pm2 stop all${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Final Summary / الملخص النهائي
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

show_summary() {
    local fe_port="$PORT"
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ${BOLD}مأمون يعمل! / MAMOUN Multi-Brain AGI is running!${NC}"
    echo -e "${SILVER}  Dashboard:  http://localhost:${fe_port}${NC}"
    echo -e "${SILVER}  الباك إند:  http://localhost:${BACKEND_PORT}${NC}"
    echo -e "${SILVER}  API Docs:   http://localhost:${BACKEND_PORT}/docs${NC}"
    echo -e "${SILVER}  الصحة:      http://localhost:${BACKEND_PORT}/health${NC}"
    echo -e "${SILVER}  المقاييس:   http://localhost:${BACKEND_PORT}/metrics${NC}"
    echo -e "${GRAY}  السجلات:    ${LOG_DIR}/${NC}"
    echo -e "${GRAY}  الوضع:      ${MODE}${NC}"
    echo -e "${GRAY}  إيقاف:      ./startup.sh stop${NC}"
    echo -e "${GRAY}  حالة:       ./startup.sh status${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# Parse Arguments / تحليل المعاملات
# ═══════════════════════════════════════════════════════════════════════════════════════════════════

COMMAND="${1:-start}"
shift || true

# Check for --prod flag
for arg in "$@"; do
    case "$arg" in
        --prod|--production|-p)
            MODE="prod"
            export PORT="${PORT:-${PROD_PORT}}"
            ;;
    esac
done

show_banner

case "$COMMAND" in
    start)
        load_env
        start_backend
        start_frontend
        run_health_checks
        show_summary
        ;;

    stop)
        stop_services
        ;;

    restart)
        stop_services
        sleep 2
        load_env
        start_backend
        start_frontend
        run_health_checks
        show_summary
        ;;

    status)
        show_status
        ;;

    build)
        load_env
        build_frontend
        log_ok "البناء مكتمل / Build complete — run './startup.sh start --prod' to start in production"
        ;;

    test)
        run_tests
        ;;

    pm2)
        load_env
        generate_pm2_config
        start_pm2
        ;;

    health)
        run_health_checks
        ;;

    api-test)
        run_api_tests
        ;;

    venv)
        setup_venv
        ;;

    *)
        echo ""
        echo -e "${BOLD}Usage / الاستخدام:${NC}"
        echo -e "  ${CYAN}./startup.sh start${NC}              Start all services (dev mode) / تشغيل كل الخدمات"
        echo -e "  ${CYAN}./startup.sh start --prod${NC}       Start all services (production) / تشغيل بالإنتاج"
        echo -e "  ${CYAN}./startup.sh stop${NC}               Stop all services / إيقاف كل الخدمات"
        echo -e "  ${CYAN}./startup.sh restart${NC}            Restart all services / إعادة التشغيل"
        echo -e "  ${CYAN}./startup.sh restart --prod${NC}     Restart in production / إعادة تشغيل بالإنتاج"
        echo -e "  ${CYAN}./startup.sh status${NC}             Show service status / عرض حالة الخدمات"
        echo -e "  ${CYAN}./startup.sh build${NC}              Build for production / بناء للإنتاج"
        echo -e "  ${CYAN}./startup.sh test${NC}               Run tests / تشغيل الاختبارات"
        echo -e "  ${CYAN}./startup.sh pm2${NC}                Generate PM2 config & start / تشغيل بـ PM2"
        echo -e "  ${CYAN}./startup.sh health${NC}             Run health checks / فحص الصحة"
        echo -e "  ${CYAN}./startup.sh api-test${NC}           Test API endpoints / اختبار نقاط الاتصال"
        echo -e "  ${CYAN}./startup.sh venv${NC}               Setup Python venv only / إعداد البيئة الافتراضية فقط"
        echo ""
        ;;
esac
