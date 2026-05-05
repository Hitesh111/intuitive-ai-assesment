"""
vm_lifecycle/views.py
=====================
HTTP layer only — request parsing, response building, routing.
All business logic lives in helpers.py.
"""

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .helpers import apply_provider_status, execute_lifecycle_action, log_action
from .models import VMInstance
from .serializers import VMInstanceSerializer
from .services import OpenStackService


class VMInstanceViewSet(viewsets.ModelViewSet):
    """CRUD + lifecycle actions for OpenStack VM instances."""

    queryset = VMInstance.objects.prefetch_related("actions").all()
    serializer_class = VMInstanceSerializer
    provider = OpenStackService()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        provider_vm = self.provider.create_vm(
            name=data["name"],
            image_id=data["image_id"],
            flavor_id=data["flavor_id"],
            network_id=data["network_id"],
            key_name=data.get("key_name", ""),
        )

        vm = VMInstance.objects.create(
            **data,
            provider_instance_id=provider_vm.id,
            status=provider_vm.status,
        )
        log_action(vm, "PROVISION", {"provider_id": provider_vm.id})

        return Response(self.get_serializer(vm).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        vm = self.get_object()
        conflict, provider_vm = execute_lifecycle_action(
            vm, "START", self.provider.start_vm
        )
        return conflict or Response(self.get_serializer(vm).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        vm = self.get_object()
        conflict, provider_vm = execute_lifecycle_action(
            vm, "STOP", self.provider.stop_vm
        )
        return conflict or Response(self.get_serializer(vm).data)

    @action(detail=True, methods=["post"])
    def reboot(self, request, pk=None):
        vm = self.get_object()
        conflict, provider_vm = execute_lifecycle_action(
            vm, "REBOOT", self.provider.reboot_vm
        )
        return conflict or Response(self.get_serializer(vm).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        vm = self.get_object()
        provider_vm = self.provider.delete_vm(vm.provider_instance_id)
        apply_provider_status(vm, provider_vm)
        log_action(vm, "DELETE", {"provider_status": provider_vm.status})
        vm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
