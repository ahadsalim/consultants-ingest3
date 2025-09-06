from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import Group
from django import forms
from simple_history.admin import SimpleHistoryAdmin
from mptt.admin import MPTTModelAdmin
import os
import hashlib
import mimetypes

from .models import (
    InstrumentWork, InstrumentExpression, InstrumentManifestation,
    LegalUnit, LegalUnitVocabularyTerm, FileAsset, PinpointCitation,
    IngestLog, Chunk, ChunkEmbedding
)
from .enums import QAStatus
from ingest.admin import admin_site




class LegalUnitInline(admin.TabularInline):
    model = LegalUnit
    extra = 1
    readonly_fields = ('id', 'path_label', 'created_at', 'updated_at')


class FileAssetForm(forms.ModelForm):
    """Custom form for FileAsset with file upload functionality"""
    file_upload = forms.FileField(
        required=False,
        label='بارگذاری فایل',
        help_text='فایل مورد نظر را انتخاب کنید. پس از انتخاب، اطلاعات فایل به صورت خودکار پر می‌شود.'
    )
    
    class Meta:
        model = FileAsset
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make metadata fields readonly if file already exists
        if self.instance and self.instance.pk and self.instance.object_key:
            self.fields['bucket'].widget.attrs['readonly'] = True
            self.fields['object_key'].widget.attrs['readonly'] = True
            self.fields['original_filename'].widget.attrs['readonly'] = True
            self.fields['content_type'].widget.attrs['readonly'] = True
            self.fields['size_bytes'].widget.attrs['readonly'] = True
            self.fields['sha256'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle file upload
        if self.cleaned_data.get('file_upload'):
            uploaded_file = self.cleaned_data['file_upload']
            
            # Auto-detect content type
            content_type, _ = mimetypes.guess_type(uploaded_file.name)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Set file metadata
            instance.original_filename = uploaded_file.name
            instance.content_type = content_type
            instance.size_bytes = uploaded_file.size
            
            # Generate SHA256 hash
            sha256_hash = hashlib.sha256()
            for chunk in uploaded_file.chunks():
                sha256_hash.update(chunk)
            instance.sha256 = sha256_hash.hexdigest()
            
            # Generate object key with organized folder structure
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
                folder = 'documents'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
                folder = 'images'
            elif ext in ['.mp4', '.avi', '.mov', '.wmv']:
                folder = 'videos'
            elif ext in ['.mp3', '.wav', '.ogg']:
                folder = 'audio'
            else:
                folder = 'other'
            
            # Create unique filename
            from django.utils.timezone import now
            timestamp = now().strftime('%Y%m%d_%H%M%S')
            safe_filename = "".join(c for c in uploaded_file.name if c.isalnum() or c in '._-')
            instance.object_key = f"{folder}/{timestamp}_{safe_filename}"
            
            # Upload to MinIO
            if commit:
                self._upload_to_minio(uploaded_file, instance)
        
        if commit:
            instance.save()
        return instance
    
    def _upload_to_minio(self, uploaded_file, instance):
        """Upload file to MinIO storage"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            import boto3
            from django.conf import settings
            from botocore.config import Config
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Log MinIO configuration for debugging
            logger.info(f"MinIO Upload - Endpoint: {settings.AWS_S3_ENDPOINT_URL}")
            logger.info(f"MinIO Upload - Bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
            logger.info(f"MinIO Upload - Object Key: {instance.object_key}")
            
            # Create MinIO client
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            
            # Check if bucket exists, create if not
            try:
                s3_client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
                logger.info(f"Bucket {settings.AWS_STORAGE_BUCKET_NAME} exists")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logger.info(f"Creating bucket {settings.AWS_STORAGE_BUCKET_NAME}")
                    s3_client.create_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
                else:
                    raise
            
            # Upload file
            s3_client.upload_fileobj(
                uploaded_file,
                settings.AWS_STORAGE_BUCKET_NAME,
                instance.object_key,
                ExtraArgs={'ContentType': instance.content_type}
            )
            
            logger.info(f"Successfully uploaded file to MinIO: {instance.object_key}")
            
        except NoCredentialsError:
            error_msg = 'خطا در احراز هویت MinIO - لطفا تنظیمات کلیدها را بررسی کنید'
            logger.error(error_msg)
            from django.core.exceptions import ValidationError
            raise ValidationError(error_msg)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = f'خطا در ارتباط با MinIO (کد {error_code}): {str(e)}'
            logger.error(error_msg)
            from django.core.exceptions import ValidationError
            raise ValidationError(error_msg)
        except Exception as e:
            error_msg = f'خطا در بارگذاری فایل به MinIO: {str(e)}'
            logger.error(error_msg)
            from django.core.exceptions import ValidationError
            raise ValidationError(error_msg)


class FileAssetInline(admin.TabularInline):
    model = FileAsset
    form = FileAssetForm
    extra = 1
    readonly_fields = ('id', 'sha256', 'size_bytes', 'uploaded_by', 'created_at')


"""Removed LegalDocument admin (model deprecated)."""


"""Removed DocumentRelation admin (model deprecated)."""


class LegalUnitVocabularyTermInline(admin.TabularInline):
    """Inline admin for LegalUnit-VocabularyTerm relationship with weights."""
    model = LegalUnitVocabularyTerm
    extra = 1
    fields = ('vocabulary_term', 'weight')
    verbose_name = 'برچسب'
    verbose_name_plural = 'برچسب‌ها'


@admin.register(LegalUnit, site=admin_site)
class LegalUnitAdmin(MPTTModelAdmin, SimpleHistoryAdmin):
    list_display = ('label', 'unit_type', 'get_source_ref', 'parent', 'order_index', 'chunk_count')
    list_filter = ('unit_type', 'work', 'expr')
    search_fields = ('label', 'content', 'path_label', 'eli_fragment', 'xml_id')
    mptt_level_indent = 20
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('parent', 'unit_type', 'number', 'order_index', 'content')
        }),
        ('مراجع FRBR', {
            'fields': ('work', 'expr', 'manifestation'),
            'classes': ('collapse',)
        }),
        ('شناسه‌های Akoma Ntoso', {
            'fields': ('eli_fragment', 'xml_id'),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('path_label', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('path_label', 'created_at', 'updated_at')
    inlines = [LegalUnitVocabularyTermInline]
    
    def get_source_ref(self, obj):
        if obj.work:
            return f"Work: {obj.work.title_official}"
        return "No Reference"
    get_source_ref.short_description = 'مرجع'
    
    def chunk_count(self, obj):
        """Display the number of chunks for this legal unit."""
        return obj.chunks.count()
    chunk_count.short_description = 'تعداد چانک'

    def get_queryset(self, request):
        return super().get_queryset(request)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj)




@admin.register(FileAsset, site=admin_site)
class FileAssetAdmin(SimpleHistoryAdmin):
    form = FileAssetForm
    list_display = ('id', 'safe_original_filename', 'content_type', 'formatted_size', 'get_reference', 'uploaded_by', 'created_at')
    list_filter = ('content_type', 'created_at', 'uploaded_by')
    search_fields = ('original_filename', 'object_key', 'sha256')
    readonly_fields = ('id', 'sha256', 'formatted_size', 'created_at', 'updated_at', 'file_link', 'bucket', 'object_key', 'size_bytes')
    actions = ['delete_selected_files']
    
    # Custom form fields
    fieldsets = (
        ('بارگذاری فایل', {
            'fields': ('file_upload', 'file_link'),
            'description': 'برای آپلود فایل جدید، فایل مورد نظر را انتخاب کنید. اطلاعات فایل به صورت خودکار پر می‌شود.'
        }),
        ('اطلاعات فایل', {
            'fields': ('original_filename', 'content_type', 'formatted_size', 'sha256'),
            'classes': ('collapse',)
        }),
        ('ذخیره‌سازی MinIO', {
            'fields': ('bucket', 'object_key'),
            'classes': ('collapse',)
        }),
        ('مراجع', {
            'fields': ('legal_unit', 'manifestation'),
            'description': 'حداقل یکی از فیلدهای مرجع باید پر شود.'
        }),
        ('اطلاعات سیستم', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['uploaded_by'].initial = request.user
        return form
        
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only on create
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def formatted_size(self, obj):
        try:
            if obj.size_bytes:
                if obj.size_bytes < 1024:
                    return f"{obj.size_bytes} بایت"
                elif obj.size_bytes < 1024 * 1024:
                    return f"{obj.size_bytes / 1024:.1f} کیلوبایت"
                else:
                    return f"{obj.size_bytes / (1024 * 1024):.1f} مگابایت"
            return "-"
        except Exception as e:
            return f"Error: {str(e)}"
    formatted_size.short_description = 'حجم فایل'
    
    def file_link(self, obj):
        if obj.object_key:
            from django.utils.html import format_html
            try:
                url = obj.get_file_url()
                if url:
                    return format_html('<a href="{0}" target="_blank">مشاهده فایل</a>', url)
            except Exception as e:
                return format_html('<span style="color: red;">خطا در تولید لینک: {}</span>', str(e))
        return "هنوز فایلی آپلود نشده است"
    file_link.short_description = 'لینک فایل'
    file_link.allow_tags = True
    
    def get_reference(self, obj):
        try:
            if obj.manifestation:
                if obj.manifestation.expr and obj.manifestation.expr.work:
                    return f"Manifestation: {obj.manifestation.expr.work.title_official}"
                else:
                    return f"Manifestation: {obj.manifestation.id} (No Expression/Work)"
            elif obj.legal_unit:
                return f"Unit: {obj.legal_unit.label}"
            return "No Reference"
        except Exception as e:
            return f"Error: {str(e)}"
    get_reference.short_description = 'مرجع'

    def size_mb(self, obj):
        return f"{obj.size_bytes / (1024*1024):.2f} MB"
    size_mb.short_description = 'اندازه (MB)'
    
    def delete_selected_files(self, request, queryset):
        """Custom delete action that also removes files from MinIO"""
        deleted_count = 0
        for file_obj in queryset:
            try:
                # Delete from MinIO first
                if file_obj.object_key:
                    import boto3
                    from django.conf import settings
                    from botocore.config import Config
                    
                    s3_client = boto3.client(
                        's3',
                        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        config=Config(signature_version='s3v4'),
                        region_name='us-east-1'
                    )
                    
                    s3_client.delete_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=file_obj.object_key
                    )
                
                # Delete from database
                file_obj.delete()
                deleted_count += 1
                
            except Exception as e:
                self.message_user(request, f'خطا در حذف فایل {file_obj.original_filename}: {str(e)}', level='ERROR')
        
        if deleted_count > 0:
            self.message_user(request, f'{deleted_count} فایل با موفقیت حذف شد.')
    
    delete_selected_files.short_description = 'حذف فایل‌های انتخاب شده از MinIO و دیتابیس'
    
    def safe_original_filename(self, obj):
        """Safe display of original filename with error handling"""
        try:
            return obj.original_filename or "نام فایل موجود نیست"
        except Exception as e:
            return f"خطا: {str(e)}"
    safe_original_filename.short_description = 'نام فایل اصلی'



# FRBR Core Model Admins
@admin.register(InstrumentWork, site=admin_site)
class InstrumentWorkAdmin(SimpleHistoryAdmin):
    list_display = ('title_official', 'doc_type', 'jurisdiction', 'authority', 'local_slug', 'created_at')
    list_filter = ('doc_type', 'jurisdiction', 'authority', 'created_at')
    search_fields = ('title_official', 'local_slug', 'subject_summary')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        # Always generate slug if empty or blank
        if not obj.local_slug or obj.local_slug.strip() == '':
            # Generate slug from doc_type and title_official
            doc_type_display = obj.get_doc_type_display().lower()
            title = obj.title_official or ''
            
            # Simple transliteration
            persian_to_english = {
                'ا': 'a', 'آ': 'aa', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's',
                'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z',
                'ر': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's',
                'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f',
                'ق': 'gh', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n',
                'و': 'v', 'ه': 'h', 'ی': 'y', 'ء': '', 'ئ': 'y', 'ؤ': 'v',
                ' ': '-', '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', 
                '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
            }
            
            # Transliterate title
            english_title = ''
            for char in title.lower():
                if char in persian_to_english:
                    english_title += persian_to_english[char]
                elif char.isalnum() or char in ['-', '_']:
                    english_title += char
            
            # Clean up and limit length
            english_title = english_title.replace('--', '-').strip('-')
            if english_title:
                words = english_title.split('-')[:4]  # Take first 4 words
                english_title = '-'.join(w for w in words if w)
            
            # Create final slug
            if english_title:
                obj.local_slug = f"{doc_type_display}-{english_title}"[:90]
            else:
                # Fallback if no title
                import uuid
                obj.local_slug = f"{doc_type_display}-{str(uuid.uuid4())[:8]}"
            
        super().save_model(request, obj, form, change)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title_official', 'doc_type', 'jurisdiction', 'authority')
        }),
        ('شناسه‌ها', {
            'fields': ('local_slug', 'primary_language')
        }),
        ('شناسه‌های یکتا', {
            'fields': ('eli_uri_work', 'urn_lex'),
            'classes': ('collapse',)
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('subject_summary',),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['title_official'].help_text = 'عنوان رسمی سند را وارد کنید.'
        form.base_fields['doc_type'].help_text = 'نوع سند را از لیست انتخاب نمایید.'
        form.base_fields['jurisdiction'].help_text = 'حوزه قضایی مرتبط با این سند را انتخاب کنید.'
        form.base_fields['authority'].help_text = 'مرجع صادرکننده سند را انتخاب کنید.'
        form.base_fields['local_slug'].help_text = 'این فیلد به صورت خودکار از عنوان سند و نوع آن ساخته می‌شود.'
        form.base_fields['primary_language'].help_text = 'زبان اصلی سند را انتخاب کنید.'
        form.base_fields['eli_uri_work'].help_text = 'شناسه ELI اثر (در صورت وجود). فرمت: https://domain/country/type/year/number'
        form.base_fields['urn_lex'].help_text = 'شناسه URN LEX (در صورت وجود). فرمت: ir:authority:doc_type:yyyy-mm-dd:number'
        form.base_fields['subject_summary'].help_text = 'خلاصه‌ای از موضوع سند را وارد کنید (اختیاری).'
        return form


@admin.register(InstrumentExpression, site=admin_site)
class InstrumentExpressionAdmin(SimpleHistoryAdmin):
    list_display = ('work', 'language', 'expression_date', 'consolidation_level', 'created_at')
    list_filter = ('language', 'consolidation_level', 'created_at')
    search_fields = ('work__title_official', 'eli_uri_expr')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('work', 'language', 'consolidation_level', 'expression_date')
        }),
        ('شناسه‌های یکتا', {
            'fields': ('eli_uri_expr',),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['work'].help_text = 'سند حقوقی مرتبط با این نسخه را انتخاب کنید.'
        form.base_fields['language'].help_text = 'زبان این نسخه از سند را مشخص کنید.'
        form.base_fields['consolidation_level'].help_text = 'سطح تلفیق این نسخه را مشخص کنید (پایه، اصلاحی، تلفیقی).'
        form.base_fields['expression_date'].help_text = 'تاریخ ایجاد این نسخه از سند را وارد کنید.'
        form.base_fields['eli_uri_expr'].help_text = 'شناسه ELI این نسخه از سند (در صورت وجود).'
        return form


@admin.register(InstrumentManifestation, site=admin_site)
class InstrumentManifestationAdmin(SimpleHistoryAdmin):
    list_display = ('expr', 'publication_date', 'official_gazette_name', 'repeal_status', 'in_force_from', 'in_force_to')
    list_filter = ('publication_date', 'in_force_from', 'repeal_status', 'created_at')
    search_fields = ('expr__work__title_official', 'official_gazette_name', 'gazette_issue_no')
    readonly_fields = ('id', 'checksum_sha256', 'retrieval_date', 'created_at', 'updated_at')
    inlines = [LegalUnitInline, FileAssetInline]
    fieldsets = (
        ('اطلاعات اصلی سند', {
            'fields': ('expr', 'publication_date', 'official_gazette_name', 'gazette_issue_no', 'page_start')
        }),
        ('وضعیت سند', {
            'fields': ('repeal_status', 'in_force_from', 'in_force_to')
        }),
        ('منبع و انتشار', {
            'fields': ('source_url', 'checksum_sha256')
        }),
        ('اطلاعات سیستم', {
            'fields': ('retrieval_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Make in_force_to required if status is REPEALED
        if 'repeal_status' in form.base_fields and 'in_force_to' in form.base_fields:
            repeal_status = form.base_fields['repeal_status']
            in_force_to = form.base_fields['in_force_to']
            
            # Add JavaScript to show/hide and make required based on status
            repeal_status.widget.attrs.update({
                'onchange': "document.querySelector('#id_in_force_to').required = this.value === 'repealed';"
            })
            
            # Set initial required state
            if obj and obj.repeal_status == 'repealed':
                in_force_to.required = True
        
        return form


# Citations Admin
@admin.register(PinpointCitation, site=admin_site)
class PinpointCitationAdmin(SimpleHistoryAdmin):
    list_display = ('from_unit', 'citation_type', 'to_unit', 'created_at')
    list_filter = ('citation_type', 'created_at')
    search_fields = ('from_unit__label', 'to_unit__label', 'context_text')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'description': '<div style="background-color: #e7f3ff; border: 1px solid #b3d9ff; padding: 15px; margin-bottom: 10px; border-radius: 5px; color: #0066cc;"><strong>راهنمای تکمیل فرم:</strong><br>در این فرم وقتی یک متن حقوقی (مثلاً قانون مالیات) می‌خواهد به یک بخش مشخص از متن دیگر (مثلا ماده ۵ قانون کار) اشاره کند آنرا در اینجا ثبت می کنیم.</div>',
            'fields': ()
        }),
        ('اطلاعات ارجاع', {
            'fields': ('from_unit', 'citation_type', 'to_unit', 'context_text')
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


# Chunk and Embedding Admins

@admin.register(Chunk, site=admin_site)
class ChunkAdmin(SimpleHistoryAdmin):
    list_display = ('unit', 'token_count', 'overlap_prev', 'created_at')
    list_filter = ('expr', 'unit__unit_type', 'token_count', 'created_at')
    search_fields = ('unit__label', 'chunk_text', 'hash')
    readonly_fields = ('id', 'hash', 'created_at', 'updated_at')
    raw_id_fields = ('expr', 'unit')
    
    fieldsets = (
        ('مراجع', {
            'fields': ('expr', 'unit')
        }),
        ('محتوای چانک', {
            'fields': ('chunk_text', 'token_count', 'overlap_prev')
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('citation_payload_json', 'hash'),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ChunkEmbedding, site=admin_site)
class ChunkEmbeddingAdmin(SimpleHistoryAdmin):
    list_display = ('chunk', 'model', 'created_at')
    list_filter = ('model', 'created_at')
    search_fields = ('chunk__unit__label', 'model')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('chunk',)
    
    fieldsets = (
        ('مرجع چانک', {
            'fields': ('chunk',)
        }),
        ('تعبیه', {
            'fields': ('model', 'embedding'),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# Note: All models are registered using @admin.register decorators above
# No need for additional admin_site.register() calls
