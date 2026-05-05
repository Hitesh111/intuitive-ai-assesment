# OpenStack VM Lifecycle API

> Engineering assessment proof-of-concept implementing REST APIs for OpenStack
> VM lifecycle management using **Python · Django REST Framework · PostgreSQL**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | Django 4.2 + Django REST Framework 3.15 |
| Database | PostgreSQL 16 (SQLite fallback for local dev) |
| Provider SDK | openstacksdk (stub adapter for PoC) |
| Packaging | Docker + Docker Compose |

---

## Objective Coverage

- ✅ VM lifecycle REST APIs — provision, list, retrieve, start, stop, reboot, delete
- ✅ Health probes — `GET /healthz/` (liveness) and `GET /readyz/` (DB readiness)
- ✅ Paginated list endpoint (`page` + `page_size` query params, default 20)
- ✅ Structured JSON logging for every lifecycle action and state guard rejection
- ✅ State-transition guards (HTTP 409 on invalid transitions)
- ✅ Append-only audit log per VM action
- ✅ Clean layered architecture — thin views, business logic in `helpers.py`, provider adapter in `services.py`
- ✅ JWT authentication — login, refresh, verify
- ✅ 22 unit tests + 23 live integration tests (all passing)
- ✅ DevOps packaging via Docker / Docker Compose
- ✅ Automation scripts — `setup.sh`, `run.sh`, `deploy.sh`, `test.sh`
- ✅ Architecture write-up with diagrams (`docs/architecture.md`)
- ✅ Roadmap / backlog (`docs/roadmap.md`)

---

## Repository Structure

```
essement/
├── config/                  # Django project settings & URLs
├── vm_lifecycle/
│   ├── models.py            # VMInstance + VMActionLog
│   ├── serializers.py       # DRF serializers (nested action log)
│   ├── views.py             # Thin HTTP layer — routing only
│   ├── helpers.py           # Business logic — state guards, audit log, provider orchestration
│   ├── health.py            # Health probe endpoints (/healthz/, /readyz/)
│   ├── services.py          # OpenStack provider adapter (stub PoC)
│   ├── admin.py             # Django admin registration
│   └── tests.py             # 22 unit tests
├── docs/
│   ├── architecture.md      # Architecture diagrams & design choices
│   └── roadmap.md           # Backlog beyond the time box
├── VM_Lifecycle.postman_collection.json
├── VM_Lifecycle.postman_environment.json
├── Dockerfile
├── docker-compose.yml
├── setup.sh                 # First-time project setup
├── run.sh                   # Start local dev server
├── deploy.sh                # Docker deployment (with test gate)
├── test.sh                  # Full API integration tests
├── CONTRIBUTING.md          # Contribution guide
└── requirements.txt
```

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz/` | Liveness probe (no auth required) |
| `GET` | `/readyz/` | Readiness probe — checks DB (no auth required) |
| `POST` | `/api/v1/vms/` | Provision a new VM |
| `GET` | `/api/v1/vms/` | List all VMs (paginated, 20 per page) |
| `GET` | `/api/v1/vms/{id}/` | Retrieve VM + full action history |
| `POST` | `/api/v1/vms/{id}/start/` | Start a stopped VM |
| `POST` | `/api/v1/vms/{id}/stop/` | Stop a running VM |
| `POST` | `/api/v1/vms/{id}/reboot/` | Reboot a running VM |
| `DELETE` | `/api/v1/vms/{id}/` | Delete (terminate) a VM |

### State-Transition Rules

| Action | Allowed from states |
|---|---|
| `start` | `STOPPED`, `BUILDING` |
| `stop` | `ACTIVE` |
| `reboot` | `ACTIVE` |

Attempting an invalid transition returns **HTTP 409 Conflict** with a descriptive error message.

---

## Getting Started

### Local Development

```bash
# 1. First-time setup (run once after cloning)
./setup.sh

# 2. Start the dev server
./run.sh

# 3. Run all tests (in a second terminal)
./test.sh
```

That's it. `setup.sh` handles venv creation, dependency install, migrations, and the default admin user.

**Default credentials:** `admin` / `Admin@1234`

---

### Docker Deployment

```bash
# Run tests first, then build and start containers in the background
./deploy.sh --detach

# Tail logs
./deploy.sh --logs

# Stop containers
./deploy.sh --stop
```

> `deploy.sh` runs the full test suite before building. If any test fails, the deploy aborts.

---

### Script Reference

| Script | When to use |
|---|---|
| `./setup.sh` | Once after cloning — sets up venv, deps, DB, admin user |
| `./run.sh` | Every time to start the local dev server |
| `./run.sh 9000` | Start on a custom port |
| `./test.sh` | Run full API integration tests (server must be running) |
| `./deploy.sh --detach` | Build Docker image and start in background |
| `./deploy.sh --stop` | Stop Docker containers |
| `./deploy.sh --logs` | Tail Docker container logs |

## Authentication

All VM API endpoints require a valid JWT Bearer token.

### Step 1 — Login to get a token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@1234"}' \
  | python -m json.tool | grep '"access"' | cut -d'"' -f4)
echo "Token: $TOKEN"
```

Or manually:
```bash
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@1234"}' | python -m json.tool
```

**Default credentials** (created via `python manage.py createsuperuser`):
```
username: admin
password: Admin@1234
```

### Step 2 — Use the token in requests
Add this header to every VM request:
```
Authorization: Bearer <your-access-token>
```

---

## Example Requests

> Replace `<TOKEN>` with your access token from the login step above.

### Provision a VM
```bash
curl -s -X POST http://localhost:8000/api/v1/vms/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "name": "assessment-vm",
    "image_id": "img-ubuntu-22.04",
    "flavor_id": "m1.small",
    "network_id": "net-private",
    "key_name": "assessment-key"
  }' | python -m json.tool
```

### List VMs
```bash
curl -s http://localhost:8000/api/v1/vms/ \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

### Stop a VM
```bash
curl -s -X POST http://localhost:8000/api/v1/vms/1/stop/ \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

### Start a VM
```bash
curl -s -X POST http://localhost:8000/api/v1/vms/1/start/ \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

### Reboot a VM
```bash
curl -s -X POST http://localhost:8000/api/v1/vms/1/reboot/ \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

### Delete a VM
```bash
curl -s -X DELETE http://localhost:8000/api/v1/vms/1/ \
  -H "Authorization: Bearer <TOKEN>"
```

### Invalid Transition (409 example)
```bash
# Provision (ACTIVE), then try to start again → 409 Conflict
curl -s -X POST http://localhost:8000/api/v1/vms/1/start/ \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

### Refresh an expired token
```bash
curl -s -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}' | python -m json.tool
```

---

## Running Tests

```bash
python manage.py test
```

The test suite covers:
- **Auth** — login success, wrong password → 401, unauthenticated → 401, token refresh
- **Provisioning** — success, duplicate name → 400, missing field → 400
- **List & retrieve** — correct count, action history, 404 on unknown
- **Full lifecycle** — stop → start → reboot → delete
- **State-transition guards** — 409 on start-while-active, stop-while-stopped

---

## Postman Collection

Import **both** files into Postman:

| File | Purpose |
|---|---|
| `VM_Lifecycle.postman_collection.json` | All 11 requests with test scripts |
| `VM_Lifecycle.postman_environment.json` | Environment variables (base_url, username, password, tokens) |

**Steps:**
1. Import both files in Postman
2. Select **"VM Lifecycle — Local Dev"** as the active environment
3. Run **"0a · Login"** — tokens save automatically
4. Run remaining requests in order

---

## SDLC Notes

- Requirements captured from the assessment objective.
- Provider adapter pattern (`OpenStackService`) keeps cloud SDK calls isolated — swap the stub for real `openstacksdk` calls without touching views or models.
- `@transaction.atomic` on create and delete ensures DB and provider state stay in sync.
- Audit log (`VMActionLog`) records every lifecycle action for traceability.
- State-transition guards prevent nonsensical operations at the API layer.
- Sync lifecycle operations chosen for MVP simplicity; async orchestration can be added later for production