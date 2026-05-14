#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# BABSHARQII v41.0 — سكريبت النشر: سحب + بناء + تشغيل
# استخدم هذا السكريبت على السيرفر لسحب التحديثات من GitHub وتشغيلها
#
# الاستخدام:
#   ./deploy.sh              # سحب + بناء + تشغيل (كامل)
#   ./deploy.sh pull         # سحب فقط
#   ./deploy.sh build        # بناء فقط
#   ./deploy.sh start        # تشغيل فقط
#   ./deploy.sh stop         # إيقاف
#   ./deploy.sh restart      # إعادة تشغيل
#   ./deploy.sh status       # حالة الخدمات
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ─── Configuration ────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
LOG_DIR="$PROJECT_DIR/.logs"
PID_DIR="$PROJECT_DIR/.pids"
FRONTEND_PORT=3000
BACKEND_PORT=8000

mkdir -p "$LOG_DIR" "$PID_DIR" "$BACKEND_DIR/data" "$BACKEND_DIR/logs" "$BACKEND_DIR/sandbox"

# ─── Colors ───────────────────────────────────────────────────────────────────
PINK='\033[38;5;199m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Helpers ──────────────────────────────────────────────────────────────────
log_step()  { echo -e "  ${PINK}[→]${NC} $1"; }
log_ok()    { echo -e "  ${GREEN}[✓]${NC} $1"; }
log_err()   { echo -e "  ${RED}[✗]${NC} $1"; }
log_warn()  { echo -e "  ${YELLOW}[⚠]${NC} $1"; }

is_alive() {
    local pid="$1"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
    local file="$1"
    [ -f "$file" ] && cat "$file" 2>/dev/null || echo ""
}

# ─── Load .env ────────────────────────────────────────────────────────────────
load_env() {
    if [ -f "$BACKEND_DIR/.env" ]; then
        export $(grep -v '^#' "$BACKEND_DIR/.env" | xargs) 2>/dev/null || true
        log_ok "Loaded .env"
    elif [ -f "$PROJECT_DIR/.env" ]; then
        export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs) 2>/dev/null || true
        log_ok "Loaded .env from project root"
    fi
}

# ─── Pull from GitHub ────────────────────────────────────────────────────────
pull_updates() {
    echo ""
    echo -e "${PINK}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${PINK}║${NC}  ${BOLD}سحب التحديثات من GitHub${NC}                          ${PINK}║${NC}"
    echo -e "${PINK}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    cd "$PROJECT_DIR"

    # Check for local changes
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        log_warn "توجد تغييرات محلية — حفظ مؤقت..."
        git stash push -m "auto-stash before deploy $(date +%s)" 2>/dev/null || true
    fi

    log_step "سحب من origin/main..."
    if git pull origin main 2>&1; then
        log_ok "تم السحب بنجاح"
    else
        log_err "فشل السحب — تحقق من الاتصال والتوكن"
        exit 1
    fi

    # Restore stash if any
    if git stash list 2>/dev/null | head -1 | grep -q "auto-stash"; then
        log_step "استعادة التغييرات المحلية..."
        git stash pop 2>/dev/null || true
    fi

    log_ok "أحدث إصدار: $(git log --oneline -1)"
}

# ─── Install Dependencies ────────────────────────────────────────────────────
install_deps() {
    log_step "تثبيت تبعيات Node.js..."
    cd "$PROJECT_DIR"
    npm install --production=false 2>&1 | tail -5
    log_ok "تم تثبيت التبعيات"

    log_step "تثبيت تبعيات Python..."
    cd "$BACKEND_DIR"
    if [ -f "requirements.txt" ]; then
        pip3 install -q -r requirements.txt 2>&1 | tail -5 || log_warn "بعض تبعيات Python لم تُثبت"
    fi
    log_ok "تم تثبيت تبعيات Python"
}

# ─── Build Frontend ──────────────────────────────────────────────────────────
build_frontend() {
    log_step "بناء الواجهة الأمامية (Next.js)..."
    cd "$PROJECT_DIR"
    if npx next build 2>&1 | tail -5; then
        log_ok "تم البناء بنجاح"
    else
        log_err "فشل البناء — تحقق من الأخطاء أعلاه"
        exit 1
    fi
}

# ─── Start Backend ───────────────────────────────────────────────────────────
start_backend() {
    local pid
    pid=$(read_pid "$PID_DIR/backend.pid")
    if is_alive "$pid"; then
        log_warn "الباك إند يعمل بالفعل (PID: $pid)"
        return
    fi

    log_step "تشغيل الباك إند (FastAPI)..."
    load_env
    cd "$BACKEND_DIR"
    python3 -m uvicorn mamoun.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload >> "$LOG_DIR/backend.log" 2>&1 &
    local be_pid=$!
    echo "$be_pid" > "$PID_DIR/backend.pid"

    # Wait for backend to start
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
            log_ok "الباك إند يعمل (http://localhost:$BACKEND_PORT) — PID: $be_pid"
            return
        fi
        sleep 1
    done
    log_warn "الباك إند لم يستجب خلال 30 ثانية — تحقق من السجل: $LOG_DIR/backend.log"
}

# ─── Start Frontend ──────────────────────────────────────────────────────────
start_frontend() {
    local pid
    pid=$(read_pid "$PID_DIR/frontend.pid")
    if is_alive "$pid"; then
        log_warn "الفرونت إند يعمل بالفعل (PID: $pid)"
        return
    fi

    log_step "تشغيل الفرونت إند (Next.js)..."
    cd "$PROJECT_DIR"
    node server.js >> "$LOG_DIR/frontend.log" 2>&1 &
    local fe_pid=$!
    echo "$fe_pid" > "$PID_DIR/frontend.pid"

    # Wait for frontend to start
    for i in $(seq 1 30); do
        if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
            log_ok "الفرونت إند يعمل (http://localhost:$FRONTEND_PORT) — PID: $fe_pid"
            return
        fi
        sleep 1
    done
    log_warn "الفرونت إند لم يستجب خلال 30 ثانية — تحقق من السجل: $LOG_DIR/frontend.log"
}

# ─── Stop Services ───────────────────────────────────────────────────────────
stop_services() {
    log_step "إيقاف الخدمات..."

    local be_pid
    be_pid=$(read_pid "$PID_DIR/backend.pid")
    if is_alive "$be_pid"; then
        kill "$be_pid" 2>/dev/null || true
        sleep 2
        is_alive "$be_pid" && kill -9 "$be_pid" 2>/dev/null || true
        rm -f "$PID_DIR/backend.pid"
        log_ok "تم إيقاف الباك إند"
    else
        log_warn "الباك إند لا يعمل"
    fi

    local fe_pid
    fe_pid=$(read_pid "$PID_DIR/frontend.pid")
    if is_alive "$fe_pid"; then
        kill "$fe_pid" 2>/dev/null || true
        sleep 2
        is_alive "$fe_pid" && kill -9 "$fe_pid" 2>/dev/null || true
        rm -f "$PID_DIR/frontend.pid"
        log_ok "تم إيقاف الفرونت إند"
    else
        log_warn "الفرونت إند لا يعمل"
    fi

    # Kill any orphans
    pkill -f "uvicorn mamoun.main:app" 2>/dev/null || true
    pkill -f "node server.js" 2>/dev/null || true

    log_ok "تم إيقاف جميع الخدمات"
}

# ─── Show Status ─────────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo -e "${PINK}════════════════════════════════════════════════════${NC}"

    # Backend
    local be_pid
    be_pid=$(read_pid "$PID_DIR/backend.pid")
    if is_alive "$be_pid"; then
        log_ok "الباك إند:  يعمل (PID: $be_pid) — http://localhost:$BACKEND_PORT"
    elif curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
        log_ok "الباك إند:  يعمل — http://localhost:$BACKEND_PORT"
    else
        log_err "الباك إند:  متوقف"
    fi

    # Frontend
    local fe_pid
    fe_pid=$(read_pid "$PID_DIR/frontend.pid")
    if is_alive "$fe_pid"; then
        log_ok "الفرونت إند: يعمل (PID: $fe_pid) — http://localhost:$FRONTEND_PORT"
    elif curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
        log_ok "الفرونت إند: يعمل — http://localhost:$FRONTEND_PORT"
    else
        log_err "الفرونت إند: متوقف"
    fi

    # API Keys status
    if curl -s "http://localhost:$BACKEND_PORT/api/v2/api-keys" > /dev/null 2>&1; then
        local keys_info
        keys_info=$(curl -s "http://localhost:$BACKEND_PORT/api/v2/api-keys" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
brains = d.get('brains', {})
active = sum(1 for b in brains.values() if b.get('has_key'))
print(f'{active}/5 أدمغة لديها مفاتيح API')
" 2>/dev/null || echo "غير معروف")
        log_ok "المفاتيح:    $keys_info"
    fi

    echo -e "${PINK}════════════════════════════════════════════════════${NC}"
    echo ""
}

# ─── Parse Arguments ─────────────────────────────────────────────────────────
case "${1:-full}" in
    pull)
        pull_updates
        ;;
    build)
        install_deps
        build_frontend
        log_ok "تم البناء"
        ;;
    start)
        load_env
        start_backend
        sleep 3
        start_frontend
        show_status
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        load_env
        start_backend
        sleep 3
        start_frontend
        show_status
        ;;
    status)
        show_status
        ;;
    full|deploy|all|*)
        echo ""
        echo -e "${PINK}╔══════════════════════════════════════════════════╗${NC}"
        echo -e "${PINK}║${NC}  ${BOLD}BABSHARQII v41.0 — نشر كامل${NC}                       ${PINK}║${NC}"
        echo -e "${PINK}║${NC}  سحب + تثبيت + بناء + تشغيل                       ${PINK}║${NC}"
        echo -e "${PINK}╚══════════════════════════════════════════════════╝${NC}"
        echo ""

        pull_updates
        install_deps
        build_frontend
        stop_services || true
        sleep 1
        load_env
        start_backend
        sleep 5
        start_frontend
        show_status

        echo ""
        echo -e "${GREEN}  ${BOLD}تم النشر بنجاح!${NC}"
        echo -e "  ${PINK}الموقع:${NC}     http://localhost:$FRONTEND_PORT"
        echo -e "  ${PINK}الباك إند:${NC}  http://localhost:$BACKEND_PORT"
        echo -e "  ${PINK}API Docs:${NC}  http://localhost:$BACKEND_PORT/docs"
        echo -e "  ${PINK}المفاتيح:${NC}  http://localhost:$FRONTEND_PORT → الإعدادات → المفاتيح"
        echo ""
        ;;
esac
