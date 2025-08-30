from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from ingest.apps.documents.models import LegalDocument, LegalUnit, FileAsset, QAEntry
from .serializers import (
    LegalDocumentSerializer, LegalUnitSerializer, 
    FileAssetSerializer, QAEntrySerializer
)


@extend_schema_view(
    list=extend_schema(summary="List legal documents", tags=["Documents"]),
    create=extend_schema(summary="Create legal document", tags=["Documents"]),
    retrieve=extend_schema(summary="Get legal document", tags=["Documents"]),
    update=extend_schema(summary="Update legal document", tags=["Documents"]),
    destroy=extend_schema(summary="Delete legal document", tags=["Documents"]),
)
class LegalDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = LegalDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'doc_type', 'jurisdiction', 'authority', 'created_by']
    search_fields = ['title', 'reference_no', 'created_by__username']
    ordering_fields = ['title', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = LegalDocument.objects.select_related(
            'jurisdiction', 'authority', 'created_by', 'reviewed_by', 'approved_by'
        ).prefetch_related('subject_terms', 'units', 'files', 'outgoing_relations')
        
        # Apply user-based filtering
        if self.request.user.is_superuser:
            return qs
        
        # Operators can only see their own documents
        if self.request.user.groups.filter(name='Operator').exists():
            return qs.filter(created_by=self.request.user)
        
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Get document units",
        description="Get all units for a specific document",
        tags=["Documents"]
    )
    @action(detail=True, methods=['get'])
    def units(self, request, pk=None):
        document = self.get_object()
        units = document.units.all()
        serializer = LegalUnitSerializer(units, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="List legal units", tags=["Documents"]),
    create=extend_schema(summary="Create legal unit", tags=["Documents"]),
    retrieve=extend_schema(summary="Get legal unit", tags=["Documents"]),
    update=extend_schema(summary="Update legal unit", tags=["Documents"]),
    destroy=extend_schema(summary="Delete legal unit", tags=["Documents"]),
)
class LegalUnitViewSet(viewsets.ModelViewSet):
    serializer_class = LegalUnitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['unit_type', 'document', 'parent']
    search_fields = ['label', 'content', 'document__title']
    ordering_fields = ['order_index', 'created_at']
    ordering = ['document', 'tree_id', 'lft']

    def get_queryset(self):
        qs = LegalUnit.objects.select_related('document', 'parent').prefetch_related('files')
        
        # Apply user-based filtering
        if self.request.user.is_superuser:
            return qs
        
        # Operators can only see units from their own documents
        if self.request.user.groups.filter(name='Operator').exists():
            return qs.filter(document__created_by=self.request.user)
        
        return qs


@extend_schema_view(
    list=extend_schema(summary="List file assets", tags=["Documents"]),
    create=extend_schema(summary="Create file asset", tags=["Documents"]),
    retrieve=extend_schema(summary="Get file asset", tags=["Documents"]),
    update=extend_schema(summary="Update file asset", tags=["Documents"]),
    destroy=extend_schema(summary="Delete file asset", tags=["Documents"]),
)
class FileAssetViewSet(viewsets.ModelViewSet):
    serializer_class = FileAssetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['content_type', 'document', 'legal_unit', 'uploaded_by']
    search_fields = ['original_filename', 'document__title', 'legal_unit__label']
    ordering_fields = ['original_filename', 'size_bytes', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = FileAsset.objects.select_related('document', 'legal_unit', 'uploaded_by')
        
        # Apply user-based filtering
        if self.request.user.is_superuser:
            return qs
        
        # Operators can only see files from their own documents/units
        if self.request.user.groups.filter(name='Operator').exists():
            return qs.filter(uploaded_by=self.request.user)
        
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
    serializer_class = QAEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'source_document', 'source_unit', 'created_by', 'tags']
    search_fields = ['question', 'answer', 'created_by__username']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = QAEntry.objects.select_related(
            'source_document', 'source_unit', 'created_by', 'reviewed_by', 'approved_by'
        ).prefetch_related('tags')
        
        # Apply user-based filtering
        if self.request.user.is_superuser:
            return qs
        
        # Operators can only see their own QA entries
        if self.request.user.groups.filter(name='Operator').exists():
            return qs.filter(created_by=self.request.user)
        
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
