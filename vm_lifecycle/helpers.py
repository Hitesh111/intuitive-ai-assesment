"""
vm_lifecycle/helpers.py
=======================
Business-logic utilities shared across the vm_lifecycle app.

Keeping these out of views.py ensures:
  - Views stay thin (HTTP in / HTTP out).
  - Business rules are independently testable.
  - Logic is reusable by management commands, Celery tasks, etc.
"""

import logging
from typing import Callable, Optional

from rest_framework import status
from rest_framework.response import Response

from .models import VMActionLog, VMInstance, VMStatus
from .services import ProviderVM

logger = logging.getLogger("vm_lifecycle")

# Maps each action name to the set of VM statuses from which it is valid.


ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "START": [VMStatus.STOPPED, VMStatus.BUILDING],
    "STOP": [VMStatus.ACTIVE],
    "REBOOT": [VMStatus.ACTIVE],
}


def check_transition(vm: VMInstance, action_name: str) -> Optional[Response]:
    """Validate that *vm* is in an allowed state for *action_name*.

    Returns:
        ``None``            — transition is valid; caller may proceed.
        ``Response(409)``   — transition is forbidden; return this to the client.
    """
    allowed = ALLOWED_TRANSITIONS.get(action_name, [])
    if allowed and vm.status not in allowed:
        logger.warning(
            "State guard rejected: vm=%s action=%s current_status=%s allowed=%s",
            vm.pk, action_name, vm.status, allowed,
        )
        return Response(
            {
                "detail": (
                    f"Cannot perform '{action_name}' on a VM in state "
                    f"'{vm.status}'. Allowed source states: {allowed}."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )
    return None




def log_action(vm: VMInstance, action: str, details: dict) -> VMActionLog:
    """Append an entry to the VM audit trail and return the created log record."""
    logger.info("VM action: vm=%s action=%s details=%s", vm.pk, action, details)
    return VMActionLog.objects.create(vm=vm, action=action, details=details)




def apply_provider_status(vm: VMInstance, provider_vm: ProviderVM) -> None:
    """Persist the status returned by the provider adapter to the database.

    Only updates the ``status`` and ``updated_at`` fields — avoids a full-row
    UPDATE on every lifecycle call.
    """
    vm.status = provider_vm.status
    vm.save(update_fields=["status", "updated_at"])


def execute_lifecycle_action(
    vm: VMInstance,
    action_name: str,
    provider_call: Callable[[str], ProviderVM],
) -> tuple[Optional[Response], Optional[ProviderVM]]:
    """Run a single lifecycle action end-to-end (guard → provider → persist → log).

    Args:
        vm:            The ``VMInstance`` to act on.
        action_name:   One of ``'START'``, ``'STOP'``, ``'REBOOT'``.
        provider_call: A callable that accepts a provider instance ID and returns
                       a ``ProviderVM`` dataclass (e.g. ``provider.stop_vm``).

    Returns:
        ``(conflict_response, None)``  — if the state transition is invalid.
        ``(None, provider_vm)``        — on success; caller builds the HTTP response.
    """
    conflict = check_transition(vm, action_name)
    if conflict:
        return conflict, None

    provider_vm = provider_call(vm.provider_instance_id)
    apply_provider_status(vm, provider_vm)
    log_action(vm, action_name, {"provider_status": provider_vm.status})
    return None, provider_vm
