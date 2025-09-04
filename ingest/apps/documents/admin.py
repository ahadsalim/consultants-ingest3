from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import Group
from simple_history.admin import SimpleHistoryAdmin
from mptt.admin import MPTTModelAdmin

from .models import (
    LegalDocument, DocumentRelation, LegalUnit, FileAsset, QAEntry,
    InstrumentWork, InstrumentExpression, InstrumentManifestation,
    InstrumentRelation, PinpointCitation, Tag, WorkTag, UnitTag,
    IngestLog, RAGChunk
)
from .enums import DocumentStatus, QAStatus
from ingest.admin import admin_site


class DocumentRelationInline(admin.TabularInline):
    model = DocumentRelation
    fk_name = 'from_document'
    extra = 1


class LegalUnitInline(admin.TabularInline):
    model = LegalUnit
    extra = 1
    readonly_fields = ('id', 'path_label', 'created_at', 'updated_at')


class FileAssetInline(admin.TabularInline):
    model = FileAsset
    extra = 1
    readonly_fields = ('id', 'sha256', 'size_bytes', 'uploaded_by', 'created_at')


@admin.register(LegalDocument, site=admin_site)
class LegalDocumentAdmin(SimpleHistoryAdmin):
    verbose_name = "سند حقوقی"
    verbose_name_plural = "📄 اسناد حقوقی"
    list_display = ('title', 'doc_type', 'jurisdiction', 'authority', 'status_badge', 'created_by', 'created_at')
    list_filter = ('status', 'doc_type', 'jurisdiction', 'authority', 'created_at')
    search_fields = ('title', 'reference_no', 'created_by__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    filter_horizontal = ('subject_terms',)
    inlines = [DocumentRelationInline, LegalUnitInline, FileAssetInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'reference_no', 'doc_type', 'jurisdiction', 'authority')
        }),
        ('تاریخ‌ها', {
            'fields': ('enactment_date', 'effective_date', 'expiry_date')
        }),
        ('وضعیت و گردش کار', {
            'fields': ('status', 'created_by', 'reviewed_by', 'approved_by')
        }),
        ('موضوعات', {
            'fields': ('subject_terms',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['submit_for_review', 'approve_documents', 'reject_documents', 'resend_to_core']

    def status_badge(self, obj):
        colors = {
            DocumentStatus.DRAFT: 'gray',
            DocumentStatus.UNDER_REVIEW: 'orange',
            DocumentStatus.APPROVED: 'green',
            DocumentStatus.REJECTED: 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Operators can only see their own documents
        if request.user.groups.filter(name='Operator').exists():
            return qs.filter(created_by=request.user)
        
        return qs

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
        
        # Superuser can change everything
        if request.user.is_superuser:
            return True
        
        # Approved documents are read-only except for admins
        if obj.status == DocumentStatus.APPROVED:
            return request.user.groups.filter(name='Admin').exists()
        
        # Operators can only edit their own documents
        if request.user.groups.filter(name='Operator').exists():
            return obj.created_by == request.user
        
        return True

    def submit_for_review(self, request, queryset):
        count = 0
        for doc in queryset:
            if doc.status == DocumentStatus.DRAFT:
                doc.status = DocumentStatus.UNDER_REVIEW
                doc.reviewed_by = None
                doc.save()
                count += 1
        self.message_user(request, f'{count} سند برای بررسی ارسال شد.')
    submit_for_review.short_description = 'ارسال برای بررسی'

    def approve_documents(self, request, queryset):
        if not request.user.groups.filter(name__in=['Reviewer', 'Admin']).exists():
            self.message_user(request, 'شما مجاز به تأیید اسناد نیستید.', level='ERROR')
            return
        
        count = 0
        for doc in queryset:
            if doc.status == DocumentStatus.UNDER_REVIEW:
                doc.status = DocumentStatus.APPROVED
                doc.approved_by = request.user
                doc.save()
                # TODO: Trigger sync job
                count += 1
        self.message_user(request, f'{count} سند تأیید شد.')
    approve_documents.short_description = 'تأیید اسناد'

    def reject_documents(self, request, queryset):
        if not request.user.groups.filter(name__in=['Reviewer', 'Admin']).exists():
            self.message_user(request, 'شما مجاز به رد اسناد نیستید.', level='ERROR')
            return
        
        count = 0
        for doc in queryset:
            if doc.status == DocumentStatus.UNDER_REVIEW:
                doc.status = DocumentStatus.REJECTED
                doc.save()
                count += 1
        self.message_user(request, f'{count} سند رد شد.')
    reject_documents.short_description = 'رد اسناد'

    def resend_to_core(self, request, queryset):
        # TODO: Implement resend to core functionality
        self.message_user(request, 'عملیات ارسال مجدد به هسته در حال پیاده‌سازی است.')
    resend_to_core.short_description = 'ارسال مجدد به هسته'


@admin.register(DocumentRelation, site=admin_site)
class DocumentRelationAdmin(SimpleHistoryAdmin):
    list_display = ('from_document', 'relation_type', 'to_document', 'created_at')
    list_filter = ('relation_type', 'created_at')
    search_fields = ('from_document__title', 'to_document__title')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(LegalUnit, site=admin_site)
class LegalUnitAdmin(MPTTModelAdmin, SimpleHistoryAdmin):
    list_display = ('label', 'unit_type', 'get_source_ref', 'parent', 'order_index')
    list_filter = ('unit_type', 'document', 'work', 'expr')
    search_fields = ('label', 'content', 'path_label', 'eli_fragment', 'xml_id')
    mptt_level_indent = 20
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('parent', 'unit_type', 'label', 'number', 'order_index', 'content')
        }),
        ('مراجع (Legacy)', {
            'fields': ('document',),
            'classes': ('collapse',)
        }),
        ('مراجع FRBR', {
            'fields': ('work', 'expr', 'manifestation'),
            'classes': ('collapse',)
        }),
        ('شناسه‌های Akoma Ntoso', {
            'fields': ('eli_fragment', 'xml_id', 'text_plain'),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('path_label', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('path_label', 'created_at', 'updated_at')
    
    def get_source_ref(self, obj):
        if obj.work:
            return f"Work: {obj.work.title_official}"
        elif obj.document:
            return f"Doc: {obj.document.title}"
        return "No Reference"
    get_source_ref.short_description = 'مرجع'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Operators can only see units from their own documents
        if request.user.groups.filter(name='Operator').exists():
            return qs.filter(document__created_by=request.user)
        
        return qs

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
        
        # Check document permissions
        return LegalDocumentAdmin().has_change_permission(request, obj.document)


@admin.register(FileAsset, site=admin_site)
class FileAssetAdmin(SimpleHistoryAdmin):
    list_display = ('original_filename', 'content_type', 'size_bytes', 'get_reference', 'uploaded_by', 'created_at')
    list_filter = ('content_type', 'created_at', 'uploaded_by')
    search_fields = ('original_filename', 'object_key', 'sha256')
    readonly_fields = ('id', 'sha256', 'size_bytes', 'created_at', 'updated_at')
    fieldsets = (
        ('اطلاعات فایل', {
            'fields': ('original_filename', 'content_type', 'size_bytes', 'sha256', 'bucket', 'object_key')
        }),
        ('مراجع (Legacy)', {
            'fields': ('document', 'legal_unit'),
            'classes': ('collapse',)
        }),
        ('مراجع FRBR', {
            'fields': ('manifestation',),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_reference(self, obj):
        if obj.manifestation:
            return f"Manifestation: {obj.manifestation.expr.work.title_official}"
        elif obj.document:
            return f"Document: {obj.document.title}"
        elif obj.legal_unit:
            return f"Unit: {obj.legal_unit.label}"
        return "No Reference"
    get_reference.short_description = 'مرجع'

    def size_mb(self, obj):
        return f"{obj.size_bytes / (1024*1024):.2f} MB"
    size_mb.short_description = 'اندازه (MB)'


@admin.register(QAEntry, site=admin_site)
class QAEntryAdmin(SimpleHistoryAdmin):
    list_display = ('question_preview', 'status_badge', 'source_document', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('question', 'answer', 'created_by__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    filter_horizontal = ('tags',)
    
    actions = ['submit_for_review', 'approve_qa_entries', 'reject_qa_entries']

    def question_preview(self, obj):
        return obj.question[:100] + '...' if len(obj.question) > 100 else obj.question
    question_preview.short_description = 'سؤال'

    def status_badge(self, obj):
        colors = {
            QAStatus.DRAFT: 'gray',
            QAStatus.UNDER_REVIEW: 'orange',
            QAStatus.APPROVED: 'green',
            QAStatus.REJECTED: 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Operators can only see their own QA entries
        if request.user.groups.filter(name='Operator').exists():
            return qs.filter(created_by=request.user)
        
        return qs

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
        
        # Superuser can change everything
        if request.user.is_superuser:
            return True
        
        # Approved QA entries are read-only except for admins
        if obj.status == QAStatus.APPROVED:
            return request.user.groups.filter(name='Admin').exists()
        
        # Operators can only edit their own QA entries
        if request.user.groups.filter(name='Operator').exists():
            return obj.created_by == request.user
        
        return True

    def submit_for_review(self, request, queryset):
        count = 0
        for qa in queryset:
            if qa.status == QAStatus.DRAFT:
                qa.status = QAStatus.UNDER_REVIEW
                qa.reviewed_by = None
                qa.save()
                count += 1
        self.message_user(request, f'{count} پرسش و پاسخ برای بررسی ارسال شد.')
    submit_for_review.short_description = 'ارسال برای بررسی'

    def approve_qa_entries(self, request, queryset):
        if not request.user.groups.filter(name__in=['Reviewer', 'Admin']).exists():
            self.message_user(request, 'شما مجاز به تأیید پرسش و پاسخ‌ها نیستید.', level='ERROR')
            return
        
        count = 0
        for qa in queryset:
            if qa.status == QAStatus.UNDER_REVIEW:
                qa.status = QAStatus.APPROVED
                qa.approved_by = request.user
                qa.save()
                # TODO: Trigger sync job
                count += 1
        self.message_user(request, f'{count} پرسش و پاسخ تأیید شد.')
    approve_qa_entries.short_description = 'تأیید پرسش و پاسخ‌ها'

    def reject_qa_entries(self, request, queryset):
        if not request.user.groups.filter(name__in=['Reviewer', 'Admin']).exists():
            self.message_user(request, 'شما مجاز به رد پرسش و پاسخ‌ها نیستید.', level='ERROR')
            return
        
        count = 0
        for qa in queryset:
            if qa.status == QAStatus.UNDER_REVIEW:
                qa.status = QAStatus.REJECTED
                qa.save()
                count += 1
        self.message_user(request, f'{count} پرسش و پاسخ رد شد.')
    reject_qa_entries.short_description = 'رد پرسش و پاسخ‌ها'


# FRBR Core Model Admins
@admin.register(InstrumentWork, site=admin_site)
class InstrumentWorkAdmin(SimpleHistoryAdmin):
    list_display = ('title_official', 'doc_type', 'jurisdiction', 'authority', 'local_slug', 'created_at')
    list_filter = ('doc_type', 'jurisdiction', 'authority', 'created_at')
    search_fields = ('title_official', 'local_slug', 'subject_summary')
    prepopulated_fields = {'local_slug': ('title_official',)}
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(InstrumentExpression, site=admin_site)
class InstrumentExpressionAdmin(SimpleHistoryAdmin):
    list_display = ('work', 'language', 'expression_date', 'consolidation_level', 'created_at')
    list_filter = ('language', 'expression_date', 'created_at')
    search_fields = ('work__title_official', 'eli_uri_expr')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(InstrumentManifestation, site=admin_site)
class InstrumentManifestationAdmin(SimpleHistoryAdmin):
    list_display = ('expr', 'publication_date', 'official_gazette_name', 'in_force_from', 'in_force_to')
    list_filter = ('publication_date', 'in_force_from', 'repeal_status', 'created_at')
    search_fields = ('expr__work__title_official', 'official_gazette_name', 'gazette_issue_no')
    readonly_fields = ('id', 'checksum_sha256', 'retrieval_date', 'created_at', 'updated_at')


# Relations and Citations Admins
@admin.register(InstrumentRelation, site=admin_site)
class InstrumentRelationAdmin(SimpleHistoryAdmin):
    list_display = ('from_work', 'relation_type', 'to_work', 'effective_date', 'created_at')
    list_filter = ('relation_type', 'effective_date', 'created_at')
    search_fields = ('from_work__title_official', 'to_work__title_official', 'notes')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PinpointCitation, site=admin_site)
class PinpointCitationAdmin(SimpleHistoryAdmin):
    list_display = ('from_unit', 'citation_type', 'to_unit', 'created_at')
    list_filter = ('citation_type', 'created_at')
    search_fields = ('from_unit__label', 'to_unit__label', 'context_text')
    readonly_fields = ('id', 'created_at', 'updated_at')


# Tagging Admins
@admin.register(Tag, site=admin_site)
class TagAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'category', 'color_display', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'رنگ'


@admin.register(WorkTag, site=admin_site)
class WorkTagAdmin(SimpleHistoryAdmin):
    list_display = ('work', 'tag', 'relevance_score', 'tagged_by', 'created_at')
    list_filter = ('tag__category', 'relevance_score', 'created_at')
    search_fields = ('work__title_official', 'tag__name', 'notes')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(UnitTag, site=admin_site)
class UnitTagAdmin(SimpleHistoryAdmin):
    list_display = ('unit', 'tag', 'relevance_score', 'tagged_by', 'created_at')
    list_filter = ('tag__category', 'relevance_score', 'created_at')
    search_fields = ('unit__label', 'tag__name', 'notes')
    readonly_fields = ('id', 'created_at', 'updated_at')


# Ingest and RAG Admins
@admin.register(IngestLog, site=admin_site)
class IngestLogAdmin(SimpleHistoryAdmin):
    list_display = ('operation_type', 'source_system', 'status', 'records_processed', 'started_by', 'created_at')
    list_filter = ('operation_type', 'status', 'source_system', 'created_at')
    search_fields = ('source_system', 'source_id', 'error_message')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('اطلاعات عملیات', {
            'fields': ('operation_type', 'source_system', 'source_id', 'status')
        }),
        ('اهداف', {
            'fields': ('target_work', 'target_expression', 'target_manifestation'),
            'classes': ('collapse',)
        }),
        ('نتایج', {
            'fields': ('records_processed', 'records_failed', 'error_message', 'metadata')
        }),
        ('اطلاعات سیستم', {
            'fields': ('started_by', 'created_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(RAGChunk, site=admin_site)
class RAGChunkAdmin(SimpleHistoryAdmin):
    list_display = ('source_unit', 'chunk_index', 'chunk_type', 'token_count', 'quality_score', 'processed_at')
    list_filter = ('chunk_type', 'embedding_model', 'quality_score', 'processed_at')
    search_fields = ('source_unit__label', 'chunk_text')
    readonly_fields = ('id', 'processed_at', 'created_at', 'updated_at')
    fieldsets = (
        ('مرجع', {
            'fields': ('source_unit', 'source_manifestation')
        }),
        ('محتوای بخش', {
            'fields': ('chunk_text', 'chunk_index', 'start_offset', 'end_offset', 'chunk_type')
        }),
        ('تعبیه و کیفیت', {
            'fields': ('embedding_model', 'embedding_vector', 'token_count', 'quality_score'),
            'classes': ('collapse',)
        }),
        ('اطلاعات پردازش', {
            'fields': ('processor_version', 'processed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# Note: All models are registered using @admin.register decorators above
# No need for additional admin_site.register() calls
