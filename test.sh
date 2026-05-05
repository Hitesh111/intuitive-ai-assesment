#!/usr/bin/env bash
# =============================================================================
#  test.sh — Full API integration test suite (live server required)
#
#  Usage:
#    ./test.sh                      → test against http://localhost:8000
#    ./test.sh http://myserver:8000 → test against a custom host
#
#  Also runs Django unit tests (pytest-style via manage.py).
#  Make sure the server is running first: ./run.sh
# =============================================================================

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'
pass()    { echo -e "  ${GREEN}✅${NC}  $1"; PASS=$((PASS+1)); }
fail()    { echo -e "  ${RED}❌${NC}  $1"; FAIL=$((FAIL+1)); }
section() { echo -e "\n${CYAN}▶ $1${NC}"; }
divider() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

BASE="${1:-http://localhost:8000}"
PASS=0
FAIL=0

divider
echo -e "${BOLD}  VM Lifecycle API — Integration Test Suite${NC}"
echo -e "  Target: ${CYAN}$BASE${NC}"
divider

# ── Helpers ───────────────────────────────────────────────────────────────────
http_status() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
json_get()    { python3 -c "import sys,json; print(json.load(sys.stdin).get('$1',''))" 2>/dev/null; }

check_status() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    pass "$label  (HTTP $actual)"
  else
    fail "$label  (expected $expected, got $actual)"
  fi
}

# ── Connectivity check ────────────────────────────────────────────────────────
section "Connectivity"
if ! curl -s --max-time 5 "$BASE" > /dev/null 2>&1; then
  echo -e "\n${RED}  ERROR: Cannot reach $BASE${NC}"
  echo "  Make sure the server is running first:  ./run.sh"
  echo ""
  divider
  exit 1
fi
pass "Server reachable at $BASE"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Authentication
# ─────────────────────────────────────────────────────────────────────────────
section "Authentication"

# 1a. Unauthenticated → 401
STATUS=$(http_status "$BASE/api/v1/vms/")
check_status "Unauthenticated GET /api/v1/vms/ → 401" "401" "$STATUS"

# 1b. Login with valid credentials
LOGIN_RESP=$(curl -s -X POST "$BASE/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@1234"}')
ACCESS=$(echo "$LOGIN_RESP" | json_get "access")
REFRESH=$(echo "$LOGIN_RESP" | json_get "refresh")

if [ -n "$ACCESS" ] && [ "$ACCESS" != "null" ]; then
  pass "Login POST /api/auth/login/ → 200, access + refresh tokens"
else
  fail "Login failed — response: $LOGIN_RESP"
  echo -e "\n${RED}  Cannot proceed without a valid token.${NC}"
  echo "  Make sure 'admin' user exists: ./setup.sh"
  divider
  exit 1
fi

AUTH="Authorization: Bearer $ACCESS"

# 1c. Wrong password → 401
STATUS=$(http_status -X POST "$BASE/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrongpass"}')
check_status "Wrong password → 401" "401" "$STATUS"

# 1d. Token refresh → 200
STATUS=$(http_status -X POST "$BASE/api/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH\"}")
check_status "POST /api/auth/refresh/ → 200" "200" "$STATUS"

# 1e. Token verify → 200
STATUS=$(http_status -X POST "$BASE/api/auth/verify/" \
  -H "Content-Type: application/json" \
  -d "{\"token\":\"$ACCESS\"}")
check_status "POST /api/auth/verify/ → 200" "200" "$STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Provision VM
# ─────────────────────────────────────────────────────────────────────────────
section "Provision VM"

# 2a. Provision valid VM
VM_NAME="sh-test-vm-$$"
RESP=$(curl -s -X POST "$BASE/api/v1/vms/" \
  -H "Content-Type: application/json" \
  -H "$AUTH" \
  -d "{\"name\":\"$VM_NAME\",\"image_id\":\"img-ubuntu-22.04\",\"flavor_id\":\"m1.small\",\"network_id\":\"net-private\",\"key_name\":\"test-key\"}")
VM_ID=$(echo "$RESP" | json_get "id")
VM_STATUS=$(echo "$RESP" | json_get "status")

if [ -n "$VM_ID" ] && [ "$VM_STATUS" = "ACTIVE" ]; then
  pass "POST /api/v1/vms/ → 201, status=ACTIVE, id=$VM_ID"
else
  fail "Provision VM failed (id=$VM_ID, status=$VM_STATUS, resp=$RESP)"
  divider; exit 1
fi

# 2b. Provision audit log present
ACTIONS=$(echo "$RESP" | python3 -c "
import sys,json
d = json.load(sys.stdin)
actions = [a['action'] for a in d.get('actions',[])]
print('yes' if 'PROVISION' in actions else 'no')
" 2>/dev/null)
if [ "$ACTIONS" = "yes" ]; then
  pass "PROVISION action recorded in audit log"
else
  fail "PROVISION action missing from audit log"
fi

# 2c. Duplicate name → 400
STATUS=$(http_status -X POST "$BASE/api/v1/vms/" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d "{\"name\":\"$VM_NAME\",\"image_id\":\"i\",\"flavor_id\":\"f\",\"network_id\":\"n\"}")
check_status "Duplicate VM name → 400" "400" "$STATUS"

# 2d. Missing required fields → 400
STATUS=$(http_status -X POST "$BASE/api/v1/vms/" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"name":""}')
check_status "Missing required fields → 400" "400" "$STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — List & Retrieve
# ─────────────────────────────────────────────────────────────────────────────
section "List & Retrieve"

# 3a. List VMs → 200
STATUS=$(http_status "$BASE/api/v1/vms/" -H "$AUTH")
check_status "GET /api/v1/vms/ → 200" "200" "$STATUS"

# 3b. Retrieve VM + action history
RESP=$(curl -s "$BASE/api/v1/vms/$VM_ID/" -H "$AUTH")
HAS_ACTIONS=$(echo "$RESP" | python3 -c "
import sys,json; d=json.load(sys.stdin); print('yes' if isinstance(d.get('actions',[]), list) else 'no')
" 2>/dev/null)
STATUS=$(http_status "$BASE/api/v1/vms/$VM_ID/" -H "$AUTH")
if [ "$STATUS" = "200" ] && [ "$HAS_ACTIONS" = "yes" ]; then
  pass "GET /api/v1/vms/$VM_ID/ → 200, action history present"
else
  fail "Retrieve VM failed (status=$STATUS, has_actions=$HAS_ACTIONS)"
fi

# 3c. Retrieve non-existent → 404
STATUS=$(http_status "$BASE/api/v1/vms/99999/" -H "$AUTH")
check_status "GET /api/v1/vms/99999/ → 404" "404" "$STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — State Transition Guards (409)
# ─────────────────────────────────────────────────────────────────────────────
section "State Transition Guards"

# 4a. Start already-ACTIVE → 409
STATUS=$(http_status -X POST "$BASE/api/v1/vms/$VM_ID/start/" -H "$AUTH")
check_status "Start ACTIVE VM → 409 Conflict" "409" "$STATUS"

# 4b. Reboot already-ACTIVE (valid)
STATUS=$(http_status -X POST "$BASE/api/v1/vms/$VM_ID/reboot/" -H "$AUTH")
check_status "Reboot ACTIVE VM → 200" "200" "$STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Lifecycle Flow
# ─────────────────────────────────────────────────────────────────────────────
section "VM Lifecycle Flow"

# 5a. Stop VM
RESP=$(curl -s -X POST "$BASE/api/v1/vms/$VM_ID/stop/" -H "$AUTH")
STOPPED=$(echo "$RESP" | json_get "status")
if [ "$STOPPED" = "STOPPED" ]; then
  pass "POST /stop/ → 200, status=STOPPED"
else
  fail "Stop VM failed (status=$STOPPED)"
fi

# 5b. Stop already-STOPPED → 409
STATUS=$(http_status -X POST "$BASE/api/v1/vms/$VM_ID/stop/" -H "$AUTH")
check_status "Stop STOPPED VM → 409 Conflict" "409" "$STATUS"

# 5c. Reboot while STOPPED → 409
STATUS=$(http_status -X POST "$BASE/api/v1/vms/$VM_ID/reboot/" -H "$AUTH")
check_status "Reboot STOPPED VM → 409 Conflict" "409" "$STATUS"

# 5d. Start VM
RESP=$(curl -s -X POST "$BASE/api/v1/vms/$VM_ID/start/" -H "$AUTH")
STARTED=$(echo "$RESP" | json_get "status")
if [ "$STARTED" = "ACTIVE" ]; then
  pass "POST /start/ → 200, status=ACTIVE"
else
  fail "Start VM failed (status=$STARTED)"
fi

# 5e. Start already-ACTIVE → 409 (again)
STATUS=$(http_status -X POST "$BASE/api/v1/vms/$VM_ID/start/" -H "$AUTH")
check_status "Start ACTIVE VM again → 409 Conflict" "409" "$STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — Delete VM
# ─────────────────────────────────────────────────────────────────────────────
section "Delete VM"

# 6a. Delete
STATUS=$(http_status -X DELETE "$BASE/api/v1/vms/$VM_ID/" \
  -H "$AUTH" -H "Accept: application/json")
check_status "DELETE /api/v1/vms/$VM_ID/ → 204 No Content" "204" "$STATUS"

# 6b. Retrieve after delete → 404
STATUS=$(http_status "$BASE/api/v1/vms/$VM_ID/" -H "$AUTH")
check_status "Retrieve deleted VM → 404" "404" "$STATUS"

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — Django Unit Tests
# ─────────────────────────────────────────────────────────────────────────────
section "Django Unit Tests"

if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo ""
  python manage.py test --verbosity=1 2>&1 | tail -5
  if echo "$(python manage.py test --verbosity=0 2>&1)" | grep -q "OK"; then
    pass "All Django unit tests passed"
  else
    fail "Some Django unit tests failed — run: python manage.py test --verbosity=2"
  fi
else
  echo -e "  ${YELLOW}⚠ Skipping Django unit tests (.venv not found — run ./setup.sh first)${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────
TOTAL=$((PASS+FAIL))
echo ""
divider
echo -e "${BOLD}  Results${NC}"
divider
echo -e "  ${GREEN}Passed${NC} : $PASS"
if [ $FAIL -gt 0 ]; then
  echo -e "  ${RED}Failed${NC} : $FAIL"
else
  echo -e "  Failed : $FAIL"
fi
echo "  Total  : $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
  echo -e "  ${GREEN}${BOLD}All $TOTAL tests passed! ✅${NC}"
else
  echo -e "  ${RED}${BOLD}$FAIL test(s) failed. See details above.${NC}"
fi
divider

exit $FAIL
