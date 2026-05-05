from django.db import models


class VMStatus(models.TextChoices):
    BUILDING = 'BUILDING', 'Building'
    ACTIVE = 'ACTIVE', 'Active'
    STOPPED = 'STOPPED', 'Stopped'
    ERROR = 'ERROR', 'Error'
    DELETED = 'DELETED', 'Deleted'


class VMInstance(models.Model):
    name = models.CharField(max_length=128, unique=True)
    image_id = models.CharField(max_length=128)
    flavor_id = models.CharField(max_length=128)
    network_id = models.CharField(max_length=128)
    key_name = models.CharField(max_length=128, blank=True)
    provider_instance_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=16, choices=VMStatus.choices, default=VMStatus.BUILDING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'{self.name} ({self.status})'


class VMActionLog(models.Model):
    vm = models.ForeignKey(VMInstance, on_delete=models.CASCADE, related_name='actions')
    action = models.CharField(max_length=32)
    requested_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-requested_at']
