"""
vm_lifecycle/health.py
======================
Lightweight health check endpoints for liveness and readiness probes.
Used by load balancers, Kubernetes, and monitoring systems.

  GET /healthz/  → liveness probe (is the process alive?)
  GET /readyz/   → readiness probe (is the DB reachable?)
"""
import logging

from django.db import connection, OperationalError
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

logger = logging.getLogger("vm_lifecycle")


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def liveness(request):
    """Liveness probe — confirms the process is running."""
    return Response({"status": "ok"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def readiness(request):
    """Readiness probe — confirms the process and database are both healthy."""
    try:
        connection.ensure_connection()
        db_status = "ok"
    except OperationalError as exc:
        logger.error("Readiness check failed: %s", exc)
        return Response({"status": "degraded", "db": str(exc)}, status=503)

    logger.info("Readiness check passed")
    return Response({"status": "ok", "db": db_status})
