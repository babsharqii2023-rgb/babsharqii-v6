#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# العقل الخارق — SuperMind Launch Script
# مأمون v62 — Launches both Frontend (Next.js) and Backend (FastAPI)
# ═══════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  العقل الخارق — SuperMind Launcher${NC}"
echo -e "${CYAN}  مأمون v62 — Multi-Brain AI System${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# ─── Configuration ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FRONTEND_PORT=${FRONTEND_PORT:-3000}
BACKEND_PORT=${BACKEND_PORT:-8000}
BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}

# ─── Check .env ───────────────────────────────────────────────
check_env() {
    echo -e "${BLUE}[1/5] Checking environment...${NC}"

    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}  ⚠ No .env file found${NC}"
        echo -e "${YELLOW}  Creating .env from .env.example (if exists)...${NC}"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${GREEN}  ✓ .env created from .env.example${NC}"
        else
            # Create minimal .env
            cat > .env << 'EOF'
# SuperMind v62 — Environment Configuration
# Add your API keys below:

# GLM API Key (ZhipuAI) — Required for Neural & Symbolic Brains
GLM_API_KEY=

# DeepSeek API Key — Required for Causal & World Model Brains
DEEPSEEK_API_KEY=

# Google Gemini API Key — Required for Bayesian Brain
GEMINI_API_KEY=

# Z-AI API Key — Fallback provider
ZAI_API_KEY=

# Backend URL (used by Next.js BFF layer)
MAMOUN_BACKEND_URL=http://localhost:8000

# Frontend URL
FRONTEND_URL=http://localhost:3000
EOF
            echo -e "${GREEN}  ✓ Minimal .env created${NC}"
        fi
        echo -e "${YELLOW}  ⚠ Please edit .env and add your API keys before running!${NC}"
    else
        echo -e "${GREEN}  ✓ .env file found${NC}"
    fi
}

# ─── Install Dependencies ─────────────────────────────────────
install_deps() {
    echo -e "${BLUE}[2/5] Checking dependencies...${NC}"

    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}  ✗ Node.js not found! Please install Node.js 18+${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Node.js $(node --version)${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}  ✗ Python3 not found! Please install Python 3.10+${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Python $(python3 --version)${NC}"

    # Install frontend dependencies
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}  Installing frontend dependencies...${NC}"
        npm install
        echo -e "${GREEN}  ✓ Frontend dependencies installed${NC}"
    else
        echo -e "${GREEN}  ✓ Frontend node_modules exists${NC}"
    fi

    # Install backend dependencies
    if [ -f "backend/requirements.txt" ]; then
        echo -e "${YELLOW}  Checking backend Python dependencies...${NC}"
        pip3 install -q fastapi uvicorn pydantic pydantic-settings pyyaml python-dotenv httpx 2>/dev/null || true
        echo -e "${GREEN}  ✓ Backend dependencies checked${NC}"
    fi
}

# ─── Create Required Directories ──────────────────────────────
create_dirs() {
    echo -e "${BLUE}[3/5] Creating required directories...${NC}"
    mkdir -p backend/data backend/logs backend/sandbox backend/backups
    echo -e "${GREEN}  ✓ Directories created${NC}"
}

# ─── Build Frontend ───────────────────────────────────────────
build_frontend() {
    echo -e "${BLUE}[4/5] Building frontend...${NC}"
    if [ ! -d ".next" ]; then
        echo -e "${YELLOW}  Running next build...${NC}"
        npx next build
        echo -e "${GREEN}  ✓ Frontend built${NC}"
    else
        echo -e "${GREEN}  ✓ .next build exists (use --rebuild to rebuild)${NC}"
    fi
}

# ─── Start Services ───────────────────────────────────────────
start_services() {
    echo -e "${BLUE}[5/5] Starting services...${NC}"
    echo ""

    # Check if --frontend-only or --backend-only flags
    MODE="all"
    if [ "$1" = "--frontend-only" ] || [ "$1" = "-f" ]; then
        MODE="frontend"
    elif [ "$1" = "--backend-only" ] || [ "$1" = "-b" ]; then
        MODE="backend"
    elif [ "$1" = "--dev" ] || [ "$1" = "-d" ]; then
        MODE="dev"
    elif [ "$1" = "--rebuild" ] || [ "$1" = "-r" ]; then
        echo -e "${YELLOW}  Rebuilding frontend...${NC}"
        rm -rf .next
        npx next build
        MODE="all"
    fi

    # Export backend URL for frontend
    export MAMOUN_BACKEND_URL=http://localhost:${BACKEND_PORT}

    cleanup() {
        echo ""
        echo -e "${YELLOW}  Shutting down services...${NC}"
        if [ ! -z "$FRONTEND_PID" ]; then
            kill $FRONTEND_PID 2>/dev/null || true
        fi
        if [ ! -z "$BACKEND_PID" ]; then
            kill $BACKEND_PID 2>/dev/null || true
        fi
        echo -e "${GREEN}  ✓ Services stopped${NC}"
        exit 0
    }
    trap cleanup SIGINT SIGTERM

    if [ "$MODE" = "frontend" ] || [ "$MODE" = "all" ] || [ "$MODE" = "dev" ]; then
        if [ "$MODE" = "dev" ]; then
            echo -e "${CYAN}  Starting Next.js in DEV mode on port ${FRONTEND_PORT}...${NC}"
            npx next dev -p $FRONTEND_PORT &
        else
            echo -e "${CYAN}  Starting Next.js on port ${FRONTEND_PORT}...${NC}"
            npx next start -p $FRONTEND_PORT &
        fi
        FRONTEND_PID=$!
        echo -e "${GREEN}  ✓ Frontend started (PID: ${FRONTEND_PID})${NC}"
        echo -e "${GREEN}  → http://localhost:${FRONTEND_PORT}${NC}"
    fi

    if [ "$MODE" = "backend" ] || [ "$MODE" = "all" ]; then
        echo -e "${CYAN}  Starting FastAPI backend on ${BACKEND_HOST}:${BACKEND_PORT}...${NC}"
        cd backend
        python3 run.py --host $BACKEND_HOST --port $BACKEND_PORT &
        BACKEND_PID=$!
        cd "$SCRIPT_DIR"
        echo -e "${GREEN}  ✓ Backend started (PID: ${BACKEND_PID})${NC}"
        echo -e "${GREEN}  → http://localhost:${BACKEND_PORT}/health${NC}"
        echo -e "${GREEN}  → http://localhost:${BACKEND_PORT}/docs${NC}"
    fi

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🚀 العقل الخارق يعمل!${NC}"
    echo -e "${GREEN}  🚀 SuperMind is running!${NC}"
    echo ""
    if [ "$MODE" != "backend" ]; then
        echo -e "${GREEN}  Frontend: http://localhost:${FRONTEND_PORT}${NC}"
    fi
    if [ "$MODE" != "frontend" ]; then
        echo -e "${GREEN}  Backend:  http://localhost:${BACKEND_PORT}/docs${NC}"
    fi
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}  Press Ctrl+C to stop all services${NC}"
    echo ""

    # Wait for either process to exit
    wait
}

# ─── Main ─────────────────────────────────────────────────────
case "$1" in
    --help|-h)
        echo "Usage: ./launch.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no option)     Start both frontend and backend in production mode"
        echo "  --dev, -d       Start in development mode (hot reload)"
        echo "  --frontend, -f  Start only the frontend"
        echo "  --backend, -b   Start only the backend"
        echo "  --rebuild, -r   Rebuild frontend before starting"
        echo "  --check, -c     Only check configuration"
        echo "  --help, -h      Show this help message"
        ;;
    --check|-c)
        check_env
        install_deps
        create_dirs
        echo -e "${GREEN}✓ Configuration check passed!${NC}"
        ;;
    *)
        check_env
        install_deps
        create_dirs
        build_frontend
        start_services "$1"
        ;;
esac
