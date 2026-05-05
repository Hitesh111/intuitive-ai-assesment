from django.contrib import admin

from .models import VMActionLog, VMInstance


@admin.register(VMInstance)
class VMInstanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'provider_instance_id', 'created_at')
    search_fields = ('name', 'provider_instance_id')


@admin.register(VMActionLog)
class VMActionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'vm', 'action', 'requested_at', 'success')
    search_fields = ('vm__name', 'action')
