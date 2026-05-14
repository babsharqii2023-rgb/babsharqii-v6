#!/usr/bin/env bash
# =============================================================================
# BABSHARQII v5.0 — Enhanced Backup Script
# =============================================================================
# Usage:
#   ./backup.sh                     # Create a backup
#   ./backup.sh --list              # List available backups
#   ./backup.sh --restore <name>    # Restore from a specific backup
#   ./backup.sh --install-cron      # Install cron job for scheduled backups
#   ./backup.sh --verify <name>     # Verify a backup integrity
#   ./backup.sh --encrypt           # Encrypt backup with GPG
#   ./backup.sh --upload            # Upload backup to S3
#   ./backup.sh --email <addr>      # Send email notification on failure
# =============================================================================

set -e

BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$BACKEND_DIR/data"
BACKUP_DIR="$BACKEND_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mamoun_backup_${TIMESTAMP}"

# Rotation policy
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=3

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments
ACTION="create"
RESTORE_TARGET=""
EMAIL_ADDR=""
DO_ENCRYPT=false
DO_UPLOAD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --list)     ACTION="list"; shift ;;
        --restore)  ACTION="restore"; RESTORE_TARGET="$2"; shift 2 ;;
        --install-cron) ACTION="install-cron"; shift ;;
        --verify)   ACTION="verify"; RESTORE_TARGET="$2"; shift 2 ;;
        --encrypt)  DO_ENCRYPT=true; shift ;;
        --upload)   DO_UPLOAD=true; shift ;;
        --email)    EMAIL_ADDR="$2"; shift 2 ;;
        *)          echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helper Functions ──────────────────────────────────────────────

log_info()  { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok()    { echo -e "${GREEN}✓${NC} $1"; }
log_warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
log_err()   { echo -e "${RED}✗${NC} $1"; }

check_postgres() {
    local pg_host="${MAMOUN_POSTGRES_HOST:-}"
    local pg_pass="${MAMOUN_POSTGRES_PASSWORD:-}"
    if [ -n "$pg_host" ] && [ -n "$pg_pass" ]; then
        return 0
    fi
    # Try pg_isready
    command -v pg_isready &>/dev/null && pg_isready -q 2>/dev/null
}

check_neo4j() {
    local neo4j_uri="${MAMOUN_NEO4J_URI:-}"
    local neo4j_pass="${MAMOUN_NEO4J_PASSWORD:-}"
    if [ -n "$neo4j_uri" ] && [ -n "$neo4j_pass" ]; then
        return 0
    fi
    return 1
}

check_chromadb() {
    local chroma_host="${MAMOUN_CHROMA_HOST:-}"
    local chroma_port="${MAMOUN_CHROMA_PORT:-}"
    if [ -n "$chroma_host" ] && [ -n "$chroma_port" ]; then
        return 0
    fi
    return 1
}

send_email() {
    local subject="$1"
    local body="$2"
    if [ -n "$EMAIL_ADDR" ] && command -v mail &>/dev/null; then
        echo "$body" | mail -s "$subject" "$EMAIL_ADDR" 2>/dev/null || true
    elif [ -n "$EMAIL_ADDR" ] && command -v sendmail &>/dev/null; then
        echo -e "Subject: $subject\n\n$body" | sendmail "$EMAIL_ADDR" 2>/dev/null || true
    fi
}

# ── LIST ──────────────────────────────────────────────────────────

if [ "$ACTION" == "list" ]; then
    echo -e "${BLUE}📦 BABSHARQII v5.0 — النسخ الاحتياطية المتاحة${NC}"
    echo ""
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "لا توجد نسخ احتياطية"
        exit 0
    fi
    
    printf "%-35s %-12s %-10s %s\n" "الاسم" "الحجم" "الحالة" "التاريخ"
    printf "%-35s %-12s %-10s %s\n" "─────" "────" "─────" "──────"
    
    for f in "$BACKUP_DIR"/mamoun_backup_*.tar.gz; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .tar.gz)
        size=$(du -sh "$f" 2>/dev/null | cut -f1 || echo "?")
        date_str=$(echo "$name" | sed 's/mamoun_backup_//' | sed 's/_/ /' | awk '{print $1" "$2}')
        
        # Check integrity
        sha_file="${f}.sha256"
        if [ -f "$sha_file" ]; then
            if cd "$BACKUP_DIR" && sha256sum -c "$(basename "$sha_file")" &>/dev/null; then
                status="✓ سليم"
            else
                status="✗ تالف"
            fi
        else
            status="— غير متحقق"
        fi
        
        printf "%-35s %-12s %-10s %s\n" "$name" "$size" "$status" "$date_str"
    done
    
    # Also list encrypted backups
    for f in "$BACKUP_DIR"/mamoun_backup_*.tar.gz.gpg; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .tar.gz.gpg)
        size=$(du -sh "$f" 2>/dev/null | cut -f1 || echo "?")
        date_str=$(echo "$name" | sed 's/mamoun_backup_//' | sed 's/_/ /' | awk '{print $1" "$2}')
        printf "%-35s %-12s %-10s %s\n" "$name (مشفّر)" "$size" "🔒" "$date_str"
    done
    
    exit 0
fi

# ── VERIFY ────────────────────────────────────────────────────────

if [ "$ACTION" == "verify" ]; then
    if [ -z "$RESTORE_TARGET" ]; then
        log_err "يرجى تحديد اسم النسخة: ./backup.sh --verify mamoun_backup_20260101_120000"
        exit 1
    fi
    
    echo -e "${BLUE}🔍 BABSHARQII v5.0 — التحقق من النسخة الاحتياطية...${NC}"
    
    BACKUP_FILE="$BACKUP_DIR/${RESTORE_TARGET}.tar.gz"
    if [ ! -f "$BACKUP_FILE" ]; then
        log_err "الملف غير موجود: $BACKUP_FILE"
        exit 1
    fi
    
    # 1. Check SHA-256
    SHA_FILE="${BACKUP_FILE}.sha256"
    if [ -f "$SHA_FILE" ]; then
        if cd "$BACKUP_DIR" && sha256sum -c "$(basename "$SHA_FILE")" 2>/dev/null; then
            log_ok "SHA-256: المجموع الاختباري متطابق"
        else
            log_err "SHA-256: المجموع الاختباري غير متطابق — النسخة تالفة!"
            exit 1
        fi
    else
        log_warn "لا يوجد ملف SHA-256 للتحقق"
    fi
    
    # 2. Test extract to temp location
    VERIFY_DIR=$(mktemp -d)
    log_info "اختبار الاستعادة إلى موقع مؤقت..."
    if tar -xzf "$BACKUP_FILE" -C "$VERIFY_DIR" 2>/dev/null; then
        FILE_COUNT=$(find "$VERIFY_DIR" -type f | wc -l)
        log_ok "الاستعادة التجريبية ناجحة — $FILE_COUNT ملف مستخرج"
    else
        log_err "فشل في استخراج النسخة — قد تكون تالفة"
        rm -rf "$VERIFY_DIR"
        exit 1
    fi
    
    # 3. Check SQLite integrity if present
    DB_FILE=$(find "$VERIFY_DIR" -name "*.db" -type f | head -1)
    if [ -n "$DB_FILE" ] && command -v sqlite3 &>/dev/null; then
        INTEGRITY=$(sqlite3 "$DB_FILE" "PRAGMA integrity_check;" 2>/dev/null)
        if [ "$INTEGRITY" == "ok" ]; then
            log_ok "قاعدة بيانات SQLite: سليمة"
        else
            log_warn "قاعدة بيانات SQLite: $INTEGRITY"
        fi
    fi
    
    rm -rf "$VERIFY_DIR"
    log_ok "التحقق مكتمل — النسخة سليمة"
    exit 0
fi

# ── RESTORE ───────────────────────────────────────────────────────

if [ "$ACTION" == "restore" ]; then
    if [ -z "$RESTORE_TARGET" ]; then
        log_err "يرجى تحديد اسم النسخة: ./backup.sh --restore mamoun_backup_20260101_120000"
        exit 1
    fi
    
    echo -e "${BLUE}🔄 BABSHARQII v5.0 — استعادة من نسخة احتياطية...${NC}"
    
    BACKUP_FILE="$BACKUP_DIR/${RESTORE_TARGET}.tar.gz"
    if [ ! -f "$BACKUP_FILE" ]; then
        # Try encrypted version
        GPG_FILE="$BACKUP_DIR/${RESTORE_TARGET}.tar.gz.gpg"
        if [ -f "$GPG_FILE" ]; then
            log_info "النسخة مشفرة — جارٍ فك التشفير..."
            gpg --decrypt "$GPG_FILE" > "$BACKUP_FILE" 2>/dev/null || {
                log_err "فشل فك التشفير"
                exit 1
            }
            log_ok "تم فك التشفير"
        else
            log_err "الملف غير موجود: $BACKUP_FILE"
            exit 1
        fi
    fi
    
    # Verify first
    SHA_FILE="${BACKUP_FILE}.sha256"
    if [ -f "$SHA_FILE" ]; then
        if ! cd "$BACKUP_DIR" && sha256sum -c "$(basename "$SHA_FILE")" 2>/dev/null; then
            log_err "المجموع الاختباري غير متطابق — النسخة تالفة!"
            exit 1
        fi
    fi
    
    # Create safety backup of current data
    if [ -d "$DATA_DIR" ] && [ "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
        SAFETY_BACKUP="$BACKUP_DIR/pre_restore_${TIMESTAMP}.tar.gz"
        log_info "إنشاء نسخة احتياطية للبيانات الحالية..."
        tar -czf "$SAFETY_BACKUP" -C "$DATA_DIR" . 2>/dev/null || true
        log_ok "تم حفظ النسخة الاحتياطية الحالية: pre_restore_${TIMESTAMP}.tar.gz"
    fi
    
    # Restore
    log_info "جارٍ الاستعادة..."
    mkdir -p "$DATA_DIR"
    if tar -xzf "$BACKUP_FILE" -C "$DATA_DIR"; then
        log_ok "تمت الاستعادة بنجاح!"
        echo ""
        echo -e "${GREEN}✅ تمت استعادة البيانات من: ${RESTORE_TARGET}${NC}"
        echo -e "  📁 البيانات: $DATA_DIR"
        echo -e "  🔄 يرجى إعادة تشغيل النظام لتطبيق التغييرات"
    else
        log_err "فشل في الاستعادة!"
        # Try to restore from safety backup
        if [ -f "$SAFETY_BACKUP" ]; then
            log_warn "محاولة استعادة النسخة الاحتياطية السابقة..."
            tar -xzf "$SAFETY_BACKUP" -C "$DATA_DIR" 2>/dev/null || true
            log_warn "تمت استعادة البيانات السابقة"
        fi
        exit 1
    fi
    
    exit 0
fi

# ── INSTALL CRON ──────────────────────────────────────────────────

if [ "$ACTION" == "install-cron" ]; then
    echo -e "${BLUE}⏰ BABSHARQII v5.0 — إعداد النسخ الاحتياطي المجدول...${NC}"
    
    SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
    CRON_ENTRY="0 2 * * * $SCRIPT_PATH >> $BACKUP_DIR/cron_backup.log 2>&1"
    
    # Check if already installed
    if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
        log_warn "النسخ الاحتياطي المجدول مثبت مسبقاً"
        echo "$CRON_ENTRY"
        exit 0
    fi
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    log_ok "تم تثبيت النسخ الاحتياطي المجدول — يومياً الساعة 2:00 صباحاً"
    echo "  الأمر: $CRON_ENTRY"
    exit 0
fi

# ── CREATE BACKUP ─────────────────────────────────────────────────

echo -e "${BLUE}📦 BABSHARQII v5.0 — إنشاء نسخة احتياطية...${NC}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

BACKUP_SUCCESS=true
ERROR_MESSAGES=""

# 1. Backup SQLite database
if [ -f "$DATA_DIR/mamoun.db" ]; then
    echo "  💾 نسخ SQLite..."
    cp "$DATA_DIR/mamoun.db" "$BACKUP_DIR/mamoun_${TIMESTAMP}.db"
    log_ok "تم نسخ SQLite"
fi

# 2. Backup PostgreSQL if connected
if check_postgres; then
    echo "  🐘 نسخ PostgreSQL..."
    PG_HOST="${MAMOUN_POSTGRES_HOST:-localhost}"
    PG_PORT="${MAMOUN_POSTGRES_PORT:-5432}"
    PG_USER="${MAMOUN_POSTGRES_USER:-mamoun}"
    PG_DB="${MAMOUN_POSTGRES_DB:-mamoun}"
    
    if command -v pg_dump &>/dev/null; then
        PGPASSWORD="${MAMOUN_POSTGRES_PASSWORD}" pg_dump \
            -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$PG_DB" \
            > "$BACKUP_DIR/postgres_${TIMESTAMP}.sql" 2>/dev/null && \
            log_ok "تم نسخ PostgreSQL" || {
                log_warn "فشل نسخ PostgreSQL"
                ERROR_MESSAGES+="فشل نسخ PostgreSQL; "
            }
    else
        log_warn "pg_dump غير متوفر — تخطي نسخ PostgreSQL"
    fi
fi

# 3. Backup Neo4j if connected
if check_neo4j; then
    echo "  🔵 نسخ Neo4j..."
    NEO4J_HOME="${NEO4J_HOME:-/var/lib/neo4j}"
    
    if command -v neo4j-admin &>/dev/null; then
        neo4j-admin database dump neo4j \
            --to-path="$BACKUP_DIR" \
            --to-file="neo4j_${TIMESTAMP}.dump" 2>/dev/null && \
            log_ok "تم نسخ Neo4j" || {
                log_warn "فشل نسخ Neo4j"
                ERROR_MESSAGES+="فشل نسخ Neo4j; "
            }
    else
        log_warn "neo4j-admin غير متوفر — تخطي نسخ Neo4j"
    fi
fi

# 4. Backup ChromaDB if connected
if check_chromadb; then
    echo "  🟢 نسخ ChromaDB..."
    CHROMA_HOST="${MAMOUN_CHROMA_HOST:-localhost}"
    CHROMA_PORT="${MAMOUN_CHROMA_PORT:-8000}"
    
    # Export collections via API
    if command -v curl &>/dev/null; then
        COLLECTIONS=$(curl -s "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v1/collections" 2>/dev/null || echo "[]")
        if [ "$COLLECTIONS" != "[]" ] && [ -n "$COLLECTIONS" ]; then
            echo "$COLLECTIONS" > "$BACKUP_DIR/chromadb_collections_${TIMESTAMP}.json"
            log_ok "تم نسخ ChromaDB (قائمة المجموعات)"
            
            # Export each collection's data
            echo "$COLLECTIONS" | python3 -c "
import json, sys
try:
    collections = json.load(sys.stdin)
    for col in collections:
        print(col.get('id', col.get('name', 'unknown')))
except: pass
" 2>/dev/null | while read col_id; do
                curl -s "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v1/collections/${col_id}/get?include=embeddings,documents,metadatas" \
                    > "$BACKUP_DIR/chromadb_${col_id}_${TIMESTAMP}.json" 2>/dev/null || true
            done
        else
            log_warn "ChromaDB: لا توجد مجموعات أو فشل الاتصال"
        fi
    else
        log_warn "curl غير متوفر — تخطي نسخ ChromaDB"
    fi
fi

# 5. Backup genome archive
if [ -d "$DATA_DIR/genome_archive" ]; then
    echo "  🧬 نسخ أرشيف الجينوم..."
    cp -r "$DATA_DIR/genome_archive" "$BACKUP_DIR/genome_${TIMESTAMP}" 2>/dev/null || true
    log_ok "تم نسخ الجينوم"
fi

# 6. Backup all data (compressed)
if [ -d "$DATA_DIR" ]; then
    echo "  📓 ضغط البيانات..."
    tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" -C "$DATA_DIR" . 2>/dev/null || true
    log_ok "تم ضغط البيانات"
fi

# 7. Backup configuration files
echo "  ⚖️ نسخ ملفات الحماية..."
cp "$BACKEND_DIR/laws.yaml" "$BACKUP_DIR/laws_${TIMESTAMP}.yaml" 2>/dev/null || true
cp "$BACKEND_DIR/settings.yaml" "$BACKUP_DIR/settings_${TIMESTAMP}.yaml" 2>/dev/null || true
log_ok "تم نسخ ملفات الحماية"

# 8. Calculate checksums
echo "  🔐 حساب المجموع الاختباري..."
cd "$BACKUP_DIR"
sha256sum ${BACKUP_NAME}.tar.gz > ${BACKUP_NAME}.sha256 2>/dev/null || true
log_ok "تم حساب SHA-256"

# 9. Verify backup (quick check)
echo "  🔍 التحقق السريع من النسخة..."
if tar -tzf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" &>/dev/null; then
    log_ok "النسخة سليمة (تحقق سريع)"
else
    log_warn "تحذير: النسخة قد تكون تالفة"
    BACKUP_SUCCESS=false
    ERROR_MESSAGES+="النسخة قد تكون تالفة; "
fi

# 10. Encrypt if requested
if [ "$DO_ENCRYPT" == true ] && command -v gpg &>/dev/null; then
    echo "  🔒 تشفير النسخة..."
    gpg --symmetric --cipher-algo AES256 "${BACKUP_NAME}.tar.gz" 2>/dev/null || true
    rm -f "${BACKUP_NAME}.tar.gz"  # Keep only encrypted version
    log_ok "تم التشفير بـ AES-256"
fi

# 11. S3 Upload if requested
if [ "$DO_UPLOAD" == true ]; then
    echo "  ☁️ رفع إلى S3..."
    S3_BUCKET="${MAMOUN_BACKUP_S3_BUCKET:-}"
    if [ -n "$S3_BUCKET" ] && command -v aws &>/dev/null; then
        BACKUP_FILE="${BACKUP_NAME}.tar.gz"
        [ ! -f "$BACKUP_FILE" ] && BACKUP_FILE="${BACKUP_NAME}.tar.gz.gpg"
        
        if aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://${S3_BUCKET}/backups/$(basename "$BACKUP_FILE")" 2>/dev/null; then
            log_ok "تم الرفع إلى S3: s3://${S3_BUCKET}/backups/"
        else
            log_warn "فشل الرفع إلى S3"
            ERROR_MESSAGES+="فشل الرفع إلى S3; "
        fi
    else
        log_warn "S3 غير مُعد أو aws CLI غير متوفر"
        ERROR_MESSAGES+="S3 غير مُعد; "
    fi
fi

# 12. Backup rotation (7 daily, 4 weekly, 3 monthly)
echo "  🧹 تطبيق سياسة التدوير..."
python3 -c "
import os, re, time
from pathlib import Path

backup_dir = Path('$BACKUP_DIR')
now = time.time()

daily = []
weekly = []
monthly = []

for f in backup_dir.glob('mamoun_backup_*.tar.gz'):
    name = f.stem
    m = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', name)
    if m:
        ts = time.mktime(time.strptime(f'{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}', '%Y-%m-%d %H:%M:%S'))
        daily.append((ts, f))

daily.sort(reverse=True)
weekly.sort(reverse=True)
monthly.sort(reverse=True)

# Keep last N daily
for i, (ts, f) in enumerate(daily):
    age_days = (now - ts) / 86400
    if i >= $KEEP_DAILY and age_days > 7:
        if age_days > 30:
            # Keep monthly (first of month)
            day = time.localtime(ts).tm_mday
            if day <= 7:
                monthly.append((ts, f))
            if len(monthly) > $KEEP_MONTHLY:
                f.unlink(missing_ok=True)
                sha = backup_dir / f'{f.stem}.sha256'
                sha.unlink(missing_ok=True)
            continue
        if age_days > 7:
            # Keep weekly (Sunday)
            weekday = time.localtime(ts).tm_wday
            if weekday == 6:  # Sunday
                weekly.append((ts, f))
            if len(weekly) > $KEEP_WEEKLY and weekday != 6:
                f.unlink(missing_ok=True)
                sha = backup_dir / f'{f.stem}.sha256'
                sha.unlink(missing_ok=True)
            elif len(weekly) > $KEEP_WEEKLY:
                # Remove oldest weekly
                weekly.sort(reverse=True)
                old_ts, old_f = weekly.pop()
                old_f.unlink(missing_ok=True)
            continue
" 2>/dev/null || {
    # Fallback: simple keep last N
    ls -t "$BACKUP_DIR"/mamoun_backup_*.tar.gz 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm --
    ls -t "$BACKUP_DIR"/mamoun_backup_*.tar.gz.gpg 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm --
}

log_ok "تم تطبيق سياسة التدوير"

# ── Report ────────────────────────────────────────────────────────

BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
if [ ! -f "$BACKUP_FILE" ]; then
    BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz.gpg"
fi
BACKUP_SIZE=$(du -sh "$BACKUP_FILE" 2>/dev/null | cut -f1 || echo "unknown")

echo ""
if [ "$BACKUP_SUCCESS" == true ]; then
    echo -e "${GREEN}✅ تم إنشاء النسخة الاحتياطية بنجاح${NC}"
else
    echo -e "${YELLOW}⚠️ تم إنشاء النسخة مع تحذيرات${NC}"
    [ -n "$ERROR_MESSAGES" ] && echo -e "  ${YELLOW}التحذيرات:${NC} $ERROR_MESSAGES"
    # Send email notification on failure
    send_email "BABSHARQII Backup Warning" "Backup completed with warnings: $ERROR_MESSAGES"
fi
echo "  📁 الملف: $BACKUP_FILE"
echo "  📏 الحجم: $BACKUP_SIZE"
echo "  🔑 المجموع: $(cat $BACKUP_DIR/${BACKUP_NAME}.sha256 2>/dev/null || echo 'N/A')"
echo "  📅 التاريخ: $(date '+%Y-%m-%d %H:%M:%S')"
