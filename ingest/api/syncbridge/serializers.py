from rest_framework import serializers
from ingest.apps.syncbridge.models import SyncJob


class SyncJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncJob
        fields = [
            'id', 'job_type', 'target_id', 'payload_preview', 'status',
            'last_error', 'retry_count', 'max_retries', 'next_retry_at',
            'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'payload_preview', 'status', 'last_error', 'retry_count',
            'next_retry_at', 'completed_at', 'created_at', 'updated_at'
        ]
