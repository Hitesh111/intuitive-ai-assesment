#!/usr/bin/env bash
# =============================================================================
#  run.sh — Start the local development server
#
#  Usage:
#    ./run.sh           → starts on default port 8000
#    ./run.sh 9000      → starts on port 9000
#
#  Run setup.sh first if this is your first time.
# =============================================================================
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[run]${NC} $1"; }
warn()    { echo -e "${YELLOW}[run]${NC} $1"; }
error()   { echo -e "${RED}[run]${NC} $1"; exit 1; }
divider() { echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

PORT="${1:-8000}"

divider
echo -e "${GREEN}  VM Lifecycle API — Local Dev Server${NC}"
divider

# ── Guard: venv must exist ────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  error ".venv not found. Run ./setup.sh first."
fi

info "Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# ── Guard: .env must exist ────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  error ".env not found. Run ./setup.sh first."
fi

# ── Apply any pending migrations ──────────────────────────────────────────────
info "Checking for pending migrations..."
python manage.py migrate --run-syncdb

# ── Start server ──────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  Server starting on http://localhost:${PORT}${NC}"
echo ""
echo "  Endpoints:"
echo "    POST   /api/auth/login/           → get JWT token"
echo "    POST   /api/auth/refresh/         → refresh token"
echo "    POST   /api/v1/vms/               → provision VM"
echo "    GET    /api/v1/vms/               → list VMs"
echo "    GET    /api/v1/vms/{id}/          → retrieve VM"
echo "    POST   /api/v1/vms/{id}/start/    → start VM"
echo "    POST   /api/v1/vms/{id}/stop/     → stop VM"
echo "    POST   /api/v1/vms/{id}/reboot/   → reboot VM"
echo "    DELETE /api/v1/vms/{id}/          → delete VM"
echo ""
echo "  Credentials: admin / Admin@1234"
echo "  Press Ctrl+C to stop."
echo ""
divider

python manage.py runserver "0.0.0.0:${PORT}"
