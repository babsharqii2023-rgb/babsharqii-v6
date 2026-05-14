#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# BABSHARQII v40.0 "Mamoun" — Development Startup
# Starts Backend (with reload) + Frontend (dev server) concurrently
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  BABSHARQII v40.0 'Mamoun' — Dev Mode${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        echo -e "${GREEN}✓${NC} Created .env from .env.example — edit with your API keys"
    fi
fi

# Install if needed
if [ ! -d "$PROJECT_DIR/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd "$PROJECT_DIR" && npm install
fi

# Check Python packages
echo "Checking backend packages..."
python3 -m pip install -q fastapi uvicorn pydantic pydantic-settings pyyaml python-dotenv httpx slowapi 2>/dev/null || true

# Start both
echo ""
echo -e "${GREEN}Starting Backend (reload) + Frontend (dev)...${NC}"
echo ""

cd "$PROJECT_DIR"
npx concurrently --kill-others \
  --names "BACKEND,FRONTEND" \
  --prefix-colors "cyan,green" \
  "cd backend && python3 -m uvicorn mamoun.main:app --host 0.0.0.0 --port 8000 --reload" \
  "npx next dev -p 3000"
