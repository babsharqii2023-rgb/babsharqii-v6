#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# مأمون v62 — العقل الخارق — ملف التشغيل الشامل
# Mamoun v62 — Super Mind — Complete Launch Script
# ═══════════════════════════════════════════════════════════════════════════
#
# الاستخدام:
#   chmod +x launch.sh
#   ./launch.sh              # تشغيل كامل (باك إند + فرونت إند)
#   ./launch.sh backend      # تشغيل الباك إند فقط
#   ./launch.sh frontend     # تشغيل الفرونت إند فقط
#   ./launch.sh check        # فحص المتطلبات فقط
#   ./launch.sh install      # تثبيت المتطلبات فقط
#   ./launch.sh build        # بناء الفرونت إند للإنتاج
#   ./launch.sh production   # تشغيل في وضع الإنتاج
#
# المتطلبات:
#   - Python 3.11+
#   - Node.js 20+
#   - pip, npm
# ═══════════════════════════════════════════════════════════════════════════

set -e

# ── Colors ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Configuration ─────────────────────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)/backend"
FRONTEND_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="/tmp/mamoun-pids"
LOG_DIR="$(cd "$(dirname "$0")" && pwd)/logs"

# ── Helper Functions ──────────────────────────────────────────────────────
log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "${CYAN}[STEP]${NC} $1"; }
log_mamoun()  { echo -e "${PURPLE}[مأمون]${NC} $1"; }

# ── Create directories ────────────────────────────────────────────────────
mkdir -p "$PID_DIR" "$LOG_DIR"

# ── Check Requirements ────────────────────────────────────────────────────
check_requirements() {
    log_step "فحص المتطلبات..."
    
    local all_ok=true
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        log_info "Python: $PY_VERSION ✓"
    else
        log_error "Python 3 غير مثبت!"
        all_ok=false
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version 2>&1)
        log_info "Node.js: $NODE_VERSION ✓"
    else
        log_error "Node.js غير مثبت!"
        all_ok=false
    fi
    
    # Check npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version 2>&1)
        log_info "npm: v$NPM_VERSION ✓"
    else
        log_error "npm غير مثبت!"
        all_ok=false
    fi
    
    # Check pip
    if python3 -m pip --version &> /dev/null; then
        log_info "pip: متوفر ✓"
    else
        log_warn "pip قد لا يكون متوفراً"
    fi
    
    # Check .env file
    if [ -f ".env" ]; then
        log_info "ملف .env: موجود ✓"
    else
        log_warn "ملف .env غير موجود — يمكن إنشاؤه لاحقاً"
    fi
    
    # Check backend requirements.txt
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        log_info "Backend requirements.txt: موجود ✓"
    else
        log_warn "Backend requirements.txt غير موجود"
    fi
    
    # Check package.json
    if [ -f "package.json" ]; then
        log_info "package.json: موجود ✓"
    else
        log_error "package.json غير موجود!"
        all_ok=false
    fi
    
    if [ "$all_ok" = true ]; then
        log_info "جميع المتطلبات متوفرة ✓"
        return 0
    else
        log_error "بعض المتطلبات مفقودة!"
        return 1
    fi
}

# ── Install Dependencies ──────────────────────────────────────────────────
install_dependencies() {
    log_step "تثبيت المتطلبات..."
    
    # Install Python dependencies
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        log_mamoun "تثبيت متطلبات الباك إند..."
        pip install -q -r "$BACKEND_DIR/requirements.txt" 2>&1 | tail -3 || log_warn "بعض الحزم قد فشل تثبيتها"
        log_info "متطلبات الباك إند ✓"
    fi
    
    # Install Node.js dependencies
    if [ -f "package.json" ]; then
        log_mamoun "تثبيت متطلبات الفرونت إند..."
        npm install --silent 2>&1 | tail -3 || log_warn "بعض الحزم قد فشل تثبيتها"
        log_info "متطلبات الفرونت إند ✓"
    fi
    
    log_info "تم تثبيت جميع المتطلبات ✓"
}

# ── Start Backend ─────────────────────────────────────────────────────────
start_backend() {
    log_step "تشغيل الباك إند على المنفذ $BACKEND_PORT..."
    
    cd "$BACKEND_DIR"
    
    # Create necessary directories
    mkdir -p data logs sandbox
    
    # Start the backend using the canonical run.py (with full initialization)
    python3 run.py --host 0.0.0.0 --port $BACKEND_PORT > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$PID_DIR/backend.pid"
    
    cd "$FRONTEND_DIR"
    
    # Wait for backend to start
    log_mamoun "انتظار بدء الباك إند..."
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
            log_info "الباك إند يعمل على http://localhost:$BACKEND_PORT ✓ (PID: $BACKEND_PID)"
            return 0
        fi
        sleep 1
    done
    
    log_warn "الباك إند قد يحتاج وقتاً إضافياً للبدء — تحقق من $LOG_DIR/backend.log"
    log_info "PID الباك إند: $BACKEND_PID"
}

# ── Start Frontend ────────────────────────────────────────────────────────
start_frontend() {
    log_step "تشغيل الفرونت إند على المنفذ $FRONTEND_PORT..."
    
    # Start Next.js dev server
    npx next dev -p $FRONTEND_PORT > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
    
    # Wait for frontend to start
    log_mamoun "انتظار بدء الفرونت إند..."
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
            log_info "الفرونت إند يعمل على http://localhost:$FRONTEND_PORT ✓ (PID: $FRONTEND_PID)"
            return 0
        fi
        sleep 1
    done
    
    log_warn "الفرونت إند قد يحتاج وقتاً إضافياً — تحقق من $LOG_DIR/frontend.log"
    log_info "PID الفرونت إند: $FRONTEND_PID"
}

# ── Build for Production ──────────────────────────────────────────────────
build_frontend() {
    log_step "بناء الفرونت إند للإنتاج..."
    npm run build
    log_info "تم البناء بنجاح ✓"
}

# ── Start Production Mode ─────────────────────────────────────────────────
start_production() {
    log_step "تشغيل في وضع الإنتاج..."
    
    # Start backend
    start_backend
    
    # Start frontend (production build)
    log_mamoun "تشغيل الفرونت إند (إنتاج)..."
    npx next start -p $FRONTEND_PORT > "$LOG_DIR/frontend-prod.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
    log_info "الفرونت إند (إنتاج) يعمل على http://localhost:$FRONTEND_PORT ✓"
}

# ── Stop All ──────────────────────────────────────────────────────────────
stop_all() {
    log_step "إيقاف جميع العمليات..."
    
    if [ -f "$PID_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID"
            log_info "تم إيقاف الباك إند (PID: $BACKEND_PID)"
        fi
        rm "$PID_DIR/backend.pid"
    fi
    
    if [ -f "$PID_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID"
            log_info "تم إيقاف الفرونت إند (PID: $FRONTEND_PID)"
        fi
        rm "$PID_DIR/frontend.pid"
    fi
    
    log_info "تم إيقاف جميع العمليات ✓"
}

# ── Show Status ───────────────────────────────────────────────────────────
show_status() {
    log_mamoun "═══ حالة مأمون v62 — العقل الخارق ═══"
    echo ""
    
    # Backend status
    if [ -f "$PID_DIR/backend.pid" ]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            log_info "الباك إند: يعمل ✓ (PID: $BACKEND_PID, Port: $BACKEND_PORT)"
        else
            log_warn "الباك إند: متوقف"
        fi
    else
        log_warn "الباك إند: لم يتم تشغيله"
    fi
    
    # Frontend status
    if [ -f "$PID_DIR/frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            log_info "الفرونت إند: يعمل ✓ (PID: $FRONTEND_PID, Port: $FRONTEND_PORT)"
        else
            log_warn "الفرونت إند: متوقف"
        fi
    else
        log_warn "الفرونت إند: لم يتم تشغيله"
    fi
    
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────
clear
echo -e "${PURPLE}"
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                        ║"
echo "  ║     🧠  مأمون v62 — العقل الخارق  🧠                  ║"
echo "  ║     Mamoun v62 — Super Mind                            ║"
echo "  ║                                                        ║"
echo "  ║     5 Brains • Self-Healing • Self-Modification        ║"
echo "  ║     Deep Research • Agent Builder • Auto-Deploy         ║"
echo "  ║                                                        ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

case "${1:-all}" in
    check)
        check_requirements
        ;;
    install)
        check_requirements
        install_dependencies
        ;;
    backend)
        check_requirements
        start_backend
        echo ""
        log_mamoun "الباك إند يعمل على http://localhost:$BACKEND_PORT"
        log_mamoun "الـ API: http://localhost:$BACKEND_PORT/docs"
        log_mamoun "السجل: $LOG_DIR/backend.log"
        # Keep script running
        wait
        ;;
    frontend)
        check_requirements
        start_frontend
        echo ""
        log_mamoun "الفرونت إند يعمل على http://localhost:$FRONTEND_PORT"
        log_mamoun "السجل: $LOG_DIR/frontend.log"
        wait
        ;;
    build)
        check_requirements
        build_frontend
        ;;
    production|prod)
        check_requirements
        build_frontend
        start_production
        echo ""
        log_mamoun "═══ النظام يعمل في وضع الإنتاج ═══"
        show_status
        wait
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    all|*)
        check_requirements
        
        # Handle Ctrl+C gracefully
        trap stop_all INT TERM
        
        start_backend
        start_frontend
        
        echo ""
        log_mamoun "═══ النظام يعمل بالكامل ═══"
        echo ""
        log_info "الفرونت إند: http://localhost:$FRONTEND_PORT"
        log_info "الباك إند:   http://localhost:$BACKEND_PORT"
        log_info "توثيق API:   http://localhost:$BACKEND_PORT/docs"
        log_info "الصحة:       http://localhost:$BACKEND_PORT/health"
        echo ""
        log_mamoun "لإيقاف النظام: Ctrl+C أو ./launch.sh stop"
        log_mamoun "لحالة النظام:  ./launch.sh status"
        echo ""
        log_mamoun "السجلات:"
        log_info "  الباك إند:   $LOG_DIR/backend.log"
        log_info "  الفرونت إند: $LOG_DIR/frontend.log"
        echo ""
        
        # Keep script running
        wait
        ;;
esac
