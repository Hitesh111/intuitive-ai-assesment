# Roadmap / Backlog

## Phase 1 (MVP+) — Complete ✅
- ✅ VM lifecycle REST APIs (provision, start, stop, reboot, delete)
- ✅ JWT authentication (login, refresh, verify)
- ✅ State-transition guards (HTTP 409 on invalid operations)
- ✅ Append-only audit log per VM action
- ✅ Health probes (`/healthz/`, `/readyz/`)
- ✅ Paginated list endpoint (20 per page)
- ✅ Structured JSON logging
- ✅ Docker + Docker Compose packaging
- ✅ Automation scripts (setup, run, deploy, test)

## Phase 2 (Real OpenStack Integration)
- Swap stub adapter for authenticated `openstacksdk` calls with region scoping.
- Run integration tests against a live DevStack or MicroStack instance.
- Handle provider-side errors and map them to appropriate HTTP status codes.

## Phase 3 (Reliability & Scale)
- Move lifecycle calls to async Celery workers (Redis broker).
  - API returns `202 Accepted` immediately; client polls for status.
  - Add retry/backoff and dead-letter queue for provider errors.
- Add `X-Idempotency-Key` header to safely retry provisioning requests.
- Filtering and search on `GET /vms/` (by status, name, date range).

## Phase 4 (Security & Governance)
- RBAC — role claims in JWT; differentiate operator vs admin vs read-only.
- Tenant/project isolation — VMs scoped to the authenticated user's project.
- Audit export and retention policies (GDPR / SOC2 compliance).

## Phase 5 (Operations & Observability)
- Prometheus metrics — latency histograms, error rates, queue depth.
- Distributed tracing via OpenTelemetry.
- Alerting on failed lifecycle actions.
- Blue/green deployment + automated rollback strategy.
