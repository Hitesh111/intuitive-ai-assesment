# Architecture and Design Write-up

## Overview

This service exposes a REST API for OpenStack VM lifecycle management.
It is built with **Django + Django REST Framework** (API layer),
**PostgreSQL** (durable state & audit records), and a thin **provider
adapter** that isolates all cloud-SDK calls from business logic.

---

## Component Architecture

```mermaid
graph TD
    Client["HTTP Client\n(curl / Postman / CI)"]

    subgraph Django["Django + DRF"]
        ViewSet["VMInstanceViewSet\n(views.py)\nThin HTTP layer only"]
        Helpers["Business Logic\n(helpers.py)\nState guards · Audit log\nProvider orchestration"]
        Health["Health Probes\n(health.py)\nGET /healthz/ · GET /readyz/"]
        Serializers["Serializers\n(serializers.py)\nVMInstanceSerializer\nVMActionLogSerializer (nested)"]
        Adapter["OpenStackService\n(services.py)\ncreate_vm / start_vm\nstop_vm / reboot_vm / delete_vm\nPoC: deterministic stub\nProd: openstacksdk"]
    end

    subgraph DB["PostgreSQL"]
        VMInstance["VMInstance\nid · name · image_id · flavor_id\nnetwork_id · provider_instance_id\nstatus · metadata · timestamps"]
        VMActionLog["VMActionLog\nid · vm_fk · action\nrequested_at · success · details"]
    end

    Client -->|"REST /api/v1/vms/"| ViewSet
    Client -->|"GET /healthz/ /readyz/"| Health
    ViewSet --> Helpers
    ViewSet --> Serializers
    Helpers --> Adapter
    Helpers -->|Django ORM| VMInstance
    Helpers -->|Django ORM| VMActionLog
    VMInstance -->|"FK (cascade)"| VMActionLog
    Health -->|"DB ping"| DB
```

---

## VM Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> BUILDING : POST /vms/ (provision)
    BUILDING --> ACTIVE : provider ready
    ACTIVE --> STOPPED : POST /vms/{id}/stop/
    STOPPED --> ACTIVE : POST /vms/{id}/start/
    ACTIVE --> ACTIVE : POST /vms/{id}/reboot/
    ACTIVE --> DELETED : DELETE /vms/{id}/
    STOPPED --> DELETED : DELETE /vms/{id}/
    DELETED --> [*]

    note right of ACTIVE : reboot stays ACTIVE
    note right of BUILDING : start also allowed\nfrom BUILDING
```

> **Invalid transitions return HTTP 409 Conflict** with a descriptive error message.  
> e.g. calling `start` on an already-`ACTIVE` VM → `409 Cannot perform 'START' on a VM in state 'ACTIVE'`

---

## Request / Response Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant V as VMInstanceViewSet
    participant G as _guard()
    participant S as OpenStackService
    participant DB as PostgreSQL

    C->>V: POST /api/v1/vms/{id}/stop/
    V->>DB: SELECT VMInstance WHERE id=?
    DB-->>V: VMInstance (status=ACTIVE)
    V->>G: _guard(vm, "STOP")
    G-->>V: None (transition allowed)
    V->>S: stop_vm(provider_instance_id)
    S-->>V: ProviderVM(status=STOPPED)
    V->>DB: UPDATE VMInstance SET status=STOPPED
    V->>DB: INSERT VMActionLog(action=STOP)
    DB-->>V: ok
    V-->>C: 200 OK { status: "STOPPED", actions: [...] }
```

---

## Key Design Choices

| Decision | Rationale |
|---|---|
| **Adapter pattern** (`OpenStackService`) | Decouples API/persistence from the cloud SDK. Swap the stub for a real SDK client without touching views or models. |
| **`helpers.py` business layer** | Views stay thin (HTTP in/out only). State guards, audit logging, and provider orchestration live in helpers — independently testable and reusable by Celery tasks or management commands. |
| **`@transaction.atomic` on create & delete** | Prevents partial writes — either the DB record *and* the provider call both succeed, or neither is committed. |
| **Append-only `VMActionLog`** | Full audit trail for operational debugging, compliance, and rollback analysis. |
| **`JSONField` for `metadata` & `details`** | Schema flexibility — extensible provider-specific attributes without migrations. |
| **State-transition validation** | Guards against nonsensical operations at the API layer, returning **HTTP 409 Conflict**. |
| **Pagination (default 20)** | `GET /api/v1/vms/` is paginated to prevent unbounded responses at scale. |
| **Structured JSON logging** | Every lifecycle action and state guard rejection is logged in JSON format — drop-in compatible with ELK, Datadog, Cloud Logging. |
| **Health probes `/healthz/` `/readyz/`** | Liveness and readiness checks with no auth required — ready for Kubernetes and load balancer health checks. |
| **SQLite fallback** | `DATABASE_URL` is optional; omitting it allows zero-infrastructure local development. |

---

## Data Model

### `VMInstance`

| Field | Type | Notes |
|---|---|---|
| `name` | CharField (unique) | Human-readable identifier |
| `image_id` | CharField | Cloud image reference |
| `flavor_id` | CharField | Hardware profile reference |
| `network_id` | CharField | Network attachment |
| `key_name` | CharField (optional) | SSH key pair |
| `provider_instance_id` | CharField (unique) | ID returned by the cloud provider |
| `status` | CharField (choices) | `BUILDING / ACTIVE / STOPPED / ERROR / DELETED` |
| `metadata` | JSONField | Extensible key/value store |
| `created_at / updated_at` | DateTimeField | Auto-managed timestamps |

### `VMActionLog`

| Field | Type | Notes |
|---|---|---|
| `vm` | FK → VMInstance | Cascade delete |
| `action` | CharField | `PROVISION / START / STOP / REBOOT / DELETE` |
| `requested_at` | DateTimeField | Auto-set on creation |
| `success` | BooleanField | Default True; set False on provider error |
| `details` | JSONField | Provider response / error payload |

---

## Production Hardening (Roadmap)

- **Real OpenStack integration** — authenticated `openstacksdk` client with region scoping and credential rotation via environment secrets.
- **Async orchestration** — Celery workers for long-running operations, with retry/backoff and dead-letter queues for provider errors.
- **Idempotency keys** — `X-Idempotency-Key` header to safely retry provisioning requests.
- **RBAC** — JWT/OAuth2 bearer-token auth; project/tenant isolation.
- **Observability** — Prometheus metrics (latency, error rates) and distributed tracing via OpenTelemetry.
