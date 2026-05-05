from rest_framework import serializers

from .models import VMActionLog, VMInstance


class VMActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VMActionLog
        fields = ('id', 'action', 'requested_at', 'success', 'details')


class VMInstanceSerializer(serializers.ModelSerializer):
    actions = VMActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = VMInstance
        fields = (
            'id',
            'name',
            'image_id',
            'flavor_id',
            'network_id',
            'key_name',
            'provider_instance_id',
            'status',
            'metadata',
            'created_at',
            'updated_at',
            'actions',
        )
        read_only_fields = ('provider_instance_id', 'status', 'created_at', 'updated_at', 'actions')
