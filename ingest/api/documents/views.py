from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from ingest.apps.documents.models import (
    LegalUnit, FileAsset, QAEntry,
    InstrumentWork, InstrumentExpression, InstrumentManifestation,
)
from .serializers import (
    LegalUnitSerializer, FileAssetSerializer, QAEntrySerializer
)


"""Legacy LegalDocument API removed. Use FRBR endpoints (Work/Expression/Manifestation) if needed."""


@extend_schema_view(
    list=extend_schema(summary="List legal units", tags=["Documents"]),
    create=extend_schema(summary="Create legal unit", tags=["Documents"]),
    retrieve=extend_schema(summary="Get legal unit", tags=["Documents"]),
    update=extend_schema(summary="Update legal unit", tags=["Documents"]),
    destroy=extend_schema(summary="Delete legal unit", tags=["Documents"]),
)
class LegalUnitViewSet(viewsets.ModelViewSet):
    queryset = LegalUnit.objects.all()
    serializer_class = LegalUnitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['unit_type', 'parent', 'work', 'expr', 'manifestation']
    search_fields = ['label', 'content', 'work__title_official']
    ordering_fields = ['order_index', 'created_at', 'tree_id', 'lft']
    ordering = ['tree_id', 'lft']

    def get_queryset(self):
        qs = LegalUnit.objects.select_related('work', 'expr', 'manifestation', 'parent').prefetch_related('files')
        return qs


@extend_schema_view(
    list=extend_schema(summary="List file assets", tags=["Documents"]),
    create=extend_schema(summary="Create file asset", tags=["Documents"]),
    retrieve=extend_schema(summary="Get file asset", tags=["Documents"]),
    update=extend_schema(summary="Update file asset", tags=["Documents"]),
    destroy=extend_schema(summary="Delete file asset", tags=["Documents"]),
)
class FileAssetViewSet(viewsets.ModelViewSet):
    queryset = FileAsset.objects.all()
    serializer_class = FileAssetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['content_type', 'legal_unit', 'manifestation', 'uploaded_by']
    search_fields = ['original_filename', 'legal_unit__label', 'manifestation__expr__work__title_official']
    ordering_fields = ['original_filename', 'size_bytes', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = FileAsset.objects.select_related('legal_unit', 'manifestation', 'uploaded_by')
        return qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


@extend_schema_view(
    list=extend_schema(summary="List QA entries", tags=["Documents"]),
    create=extend_schema(summary="Create QA entry", tags=["Documents"]),
    retrieve=extend_schema(summary="Get QA entry", tags=["Documents"]),
    update=extend_schema(summary="Update QA entry", tags=["Documents"]),
    destroy=extend_schema(summary="Delete QA entry", tags=["Documents"]),
)
class QAEntryViewSet(viewsets.ModelViewSet):
    queryset = QAEntry.objects.all()
    serializer_class = QAEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'source_unit', 'created_by', 'tags']
    search_fields = ['question', 'answer', 'created_by__username']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = QAEntry.objects.select_related(
            'source_unit', 'created_by', 'reviewed_by', 'approved_by'
        ).prefetch_related('tags')
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
