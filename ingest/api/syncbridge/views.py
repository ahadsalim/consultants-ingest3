from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from ingest.apps.syncbridge.models import SyncJob
from ingest.apps.syncbridge.tasks import build_payload
from .serializers import SyncJobSerializer


@extend_schema_view(
    list=extend_schema(summary="List sync jobs", tags=["Sync"]),
    retrieve=extend_schema(summary="Get sync job", tags=["Sync"]),
)
class SyncJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SyncJob.objects.all()
    serializer_class = SyncJobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'job_type']
    search_fields = ['target_id', 'last_error']
    ordering_fields = ['created_at', 'updated_at', 'completed_at']
    ordering = ['-created_at']

    @extend_schema(
        summary="Preview sync payload",
        description="Preview the payload that would be sent to core service",
        tags=["Sync"]
    )
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        job = self.get_object()
        try:
            payload = build_payload(job.job_type, str(job.target_id))
            return Response(payload)
        except Exception as e:
            return Response(
                {"error": f"Failed to build payload: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
