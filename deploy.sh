#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
# This ensures that if tests fail, the script stops and DOES NOT deploy broken code.
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[deploy]${NC} $1"; }
warn()    { echo -e "${YELLOW}[deploy]${NC} $1"; }
error()   { echo -e "${RED}[deploy]${NC} $1"; exit 1; }
divider() { echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

divider
echo -e "${GREEN}  VM Lifecycle API — Docker Deployment${NC}"
divider

MODE="${1:-}"

# ==========================================
# --stop / --logs helpers
# ==========================================

if [ "$MODE" = "--stop" ]; then
  info "Stopping containers..."
  docker compose down
  info "Done."
  exit 0
fi

if [ "$MODE" = "--logs" ]; then
  docker compose logs -f
  exit 0
fi

# ==========================================
# 1. LOCAL TEST GATE
# ==========================================
# We never deploy broken code. Run the full unit test suite first.
# If any test fails, set -e aborts the script here — Docker never runs.

echo ""
info "Running test suite..."
source .venv/bin/activate
python manage.py test --verbosity=1

info "All tests passed. Proceeding to deploy."

# ==========================================
# 2. DOCKER DAEMON CHECK
# ==========================================
# On Mac, Docker Desktop must be running (it provides the daemon).
# Start it automatically if possible, otherwise prompt the user.

if ! docker info > /dev/null 2>&1; then
  warn "Docker daemon is not running."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    warn "Starting Docker Desktop..."
    open -a "Docker Desktop" 2>/dev/null || open -a "Docker" 2>/dev/null || true
    for i in $(seq 1 30); do
      sleep 2
      docker info > /dev/null 2>&1 && break
      printf "."
    done
    echo ""
  fi
  docker info > /dev/null 2>&1 || error "Docker is still not running. Open Docker Desktop and retry."
  info "Docker is ready ✓"
fi

# ==========================================
# 3. BUILD & START CONTAINERS
# ==========================================
# Builds a fresh Docker image and starts PostgreSQL + Django.
# Use --detach to run in the background, otherwise runs in foreground.

echo ""
info "Building Docker image..."
docker compose build

echo ""
info "Starting services (PostgreSQL + Django)..."

if [ "$MODE" = "--detach" ]; then
  docker compose up -d
  sleep 4

  info "Creating default superuser inside container..."
  docker compose exec web python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin@1234')
    print('Superuser created: admin / Admin@1234')
else:
    print('Superuser already exists')
" || warn "Could not auto-create superuser. Run manually: docker compose exec web python manage.py createsuperuser"

  echo ""
  divider
  echo -e "${GREEN}  Deployment complete!${NC}"
  echo ""
  echo "  API:      http://localhost:8000/api/v1/vms/"
  echo "  Health:   http://localhost:8000/healthz/"
  echo "  Admin UI: http://localhost:8000/admin/"
  echo "  Login:    admin / Admin@1234"
  echo ""
  echo "  ./deploy.sh --logs   → tail logs"
  echo "  ./deploy.sh --stop   → stop containers"
  divider
else
  echo ""
  echo -e "${GREEN}  Stack starting. Press Ctrl+C to stop.${NC}"
  echo "  API: http://localhost:8000/api/v1/vms/"
  echo "  Login: admin / Admin@1234"
  divider
  docker compose up
fi
