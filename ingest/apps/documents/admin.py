from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import Group
from simple_history.admin import SimpleHistoryAdmin
from mptt.admin import MPTTModelAdmin

from .models import LegalDocument, DocumentRelation, LegalUnit, FileAsset, QAEntry
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


@admin.register(LegalDocument)
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


@admin.register(DocumentRelation)
class DocumentRelationAdmin(SimpleHistoryAdmin):
    list_display = ('from_document', 'relation_type', 'to_document', 'created_at')
    list_filter = ('relation_type', 'created_at')
    search_fields = ('from_document__title', 'to_document__title')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(LegalUnit)
class LegalUnitAdmin(MPTTModelAdmin, SimpleHistoryAdmin):
    list_display = ('label', 'document', 'unit_type', 'parent', 'order_index', 'created_at')
    list_filter = ('unit_type', 'document__status', 'created_at')
    search_fields = ('label', 'content', 'document__title')
    readonly_fields = ('id', 'path_label', 'created_at', 'updated_at')
    mptt_level_indent = 20

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


@admin.register(FileAsset)
class FileAssetAdmin(SimpleHistoryAdmin):
    list_display = ('original_filename', 'content_type', 'size_mb', 'document', 'legal_unit', 'uploaded_by', 'created_at')
    list_filter = ('content_type', 'created_at')
    search_fields = ('original_filename', 'document__title', 'legal_unit__label')
    readonly_fields = ('id', 'sha256', 'size_bytes', 'uploaded_by', 'created_at', 'updated_at')

    def size_mb(self, obj):
        return f"{obj.size_bytes / (1024*1024):.2f} MB"
    size_mb.short_description = 'اندازه (MB)'


@admin.register(QAEntry)
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


# Register models with custom admin site
admin_site.register(LegalDocument, LegalDocumentAdmin)
admin_site.register(DocumentRelation, DocumentRelationAdmin)
admin_site.register(LegalUnit, LegalUnitAdmin)
admin_site.register(FileAsset, FileAssetAdmin)
admin_site.register(QAEntry, QAEntryAdmin)
