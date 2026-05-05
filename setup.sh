#!/usr/bin/env bash
# =============================================================================
#  setup.sh — First-time project setup for local development
#
#  Run once after cloning the repo:
#    chmod +x setup.sh && ./setup.sh
# =============================================================================
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[setup]${NC} $1"; }
warn()    { echo -e "${YELLOW}[setup]${NC} $1"; }
error()   { echo -e "${RED}[setup]${NC} $1"; exit 1; }
divider() { echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

divider
echo -e "${GREEN}  VM Lifecycle API — Project Setup${NC}"
divider

# ── 1. Python version check ───────────────────────────────────────────────────
info "Checking Python version..."
PYTHON=$(command -v python3 || command -v python || error "Python not found")
PY_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2)
info "Using Python $PY_VERSION at $PYTHON"

# ── 2. Virtual environment ────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  info "Creating virtual environment (.venv)..."
  $PYTHON -m venv .venv
else
  warn ".venv already exists — skipping creation"
fi

info "Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# ── 3. Dependencies ───────────────────────────────────────────────────────────
info "Installing dependencies from requirements.txt..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
info "Dependencies installed ✓"

# ── 5. Database migrations ────────────────────────────────────────────────────
info "Running database migrations..."
python manage.py migrate --run-syncdb
info "Migrations applied ✓"

# ── 6. Create default superuser ───────────────────────────────────────────────
info "Creating default superuser (admin / Admin@1234)..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin@1234')
    print('Superuser created: admin / Admin@1234')
else:
    print('Superuser already exists — skipping')
"

divider
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo "  Next steps:"
echo "    ./run.sh          → start the local dev server"
echo "    ./test.sh         → run full API integration tests"
echo "    ./deploy.sh       → build and run with Docker"
echo ""
echo "  API:    http://localhost:8000/api/v1/vms/"
echo "  Login:  username=admin  password=Admin@1234"
divider
