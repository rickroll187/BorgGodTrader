#!/bin/bash
# BorgGodTrader Dashboard Launcher
# Launches the crypto trading dashboard in your default browser

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           BorgGodTrader - Crypto Trading Dashboard        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[!] No .env file found. Creating from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}[+] Created .env from .env.example${NC}"
        echo -e "${YELLOW}[!] Please edit .env with your API keys before live trading${NC}"
    fi
fi

# Check for virtual environment
if [ -d "venv" ]; then
    echo -e "${GREEN}[+] Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}[+] Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}[!] Streamlit not found. Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Set default port
PORT=${BORG_PORT:-8501}

echo -e "${GREEN}[+] Starting dashboard on port $PORT...${NC}"
echo -e "${CYAN}[*] Dashboard will open at: http://localhost:$PORT${NC}"
echo ""

# Launch streamlit
streamlit run dashboard/advanced_dashboard.py \
    --server.port=$PORT \
    --server.headless=false \
    --browser.gatherUsageStats=false \
    --theme.base=dark \
    --theme.primaryColor="#00d4aa" \
    --theme.backgroundColor="#0e1117" \
    --theme.secondaryBackgroundColor="#1a1f2e" \
    --theme.textColor="#fafafa"
