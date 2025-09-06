import uuid
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey
from simple_history.models import HistoricalRecords

from ingest.apps.masterdata.models import BaseModel, Jurisdiction, IssuingAuthority, VocabularyTerm, Language
from .enums import DocumentType, DocumentStatus, RelationType, UnitType, QAStatus, ConsolidationLevel


# FRBR Core Models - New Schema
class InstrumentWork(BaseModel):
    """FRBR Work level - abstract legal instrument concept."""
    
    class Meta:
        verbose_name = "تعریف سند حقوقی"
        verbose_name_plural = "تعریف سند حقوقی"
        
    title_official = models.CharField(max_length=500, verbose_name='عنوان رسمی')
    doc_type = models.CharField(
        max_length=20, 
        choices=DocumentType.choices, 
        default=DocumentType.LAW,
        verbose_name='نوع سند'
    )
    jurisdiction = models.ForeignKey(
        Jurisdiction, 
        on_delete=models.CASCADE, 
        related_name='instrument_works',
        verbose_name='حوزه قضایی'
    )
    authority = models.ForeignKey(
        IssuingAuthority, 
        on_delete=models.CASCADE, 
        related_name='instrument_works',
        verbose_name='مرجع صادرکننده'
    )
    eli_uri_work = models.URLField(
        blank=True, 
        verbose_name='ELI URI اثر',
        help_text='https://domain/country/type/year/number<br>مثال: https://laws.example.ir/ir/act/2020/123'
    )
    urn_lex = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='URN LEX',
        help_text='ir:authority:doc_type:yyyy-mm-dd:number<br>مثال: ir:majlis:law:2020-06-01:123'
    )
    local_slug = models.SlugField(max_length=100, unique=True, verbose_name='شناسه محلی', blank=True)
    primary_language = models.ForeignKey(
        'masterdata.Language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        verbose_name='زبان اصلی'
    )
    subject_summary = models.TextField(blank=True, verbose_name='خلاصه موضوع')
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.title_official} ({self.get_doc_type_display()})"


class InstrumentExpression(BaseModel):
    """FRBR Expression level - specific language/version of a work."""
    
    class Meta:
        verbose_name = "تعریف نسخه سند"
        verbose_name_plural = "تعریف نسخه سند"
        unique_together = ['work', 'language', 'consolidation_level', 'expression_date']
        
    work = models.ForeignKey(
        InstrumentWork,
        on_delete=models.CASCADE,
        related_name='expressions',
        verbose_name='سند حقوقی'
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='زبان'
    )
    consolidation_level = models.CharField(
        max_length=20,
        choices=ConsolidationLevel.choices,
        default=ConsolidationLevel.BASE,
        verbose_name='سطح تلفیق'
    )
    expression_date = models.DateField(verbose_name='تاریخ نسخه', null=True, blank=True)
    eli_uri_expr = models.URLField(blank=True, verbose_name='ELI URI بیان')
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.work.title_official} - {self.language} ({self.expression_date})"


class InstrumentManifestation(BaseModel):
    """FRBR Manifestation level - physical/digital embodiment."""
    
    class RepealStatus(models.TextChoices):
        IN_FORCE = 'in_force', 'جاری و لازم الاجرا'
        REPEALED = 'repealed', 'لغو یا منسوخ شده'
    
    class Meta:
        verbose_name = "تعریف انتشار سند"
        verbose_name_plural = "تعریف انتشار سند"
        constraints = [
            models.CheckConstraint(
                check=models.Q(in_force_to__gte=models.F('in_force_from')) | models.Q(in_force_to__isnull=True),
                name='valid_in_force_period'
            )
        ]
        
    expr = models.ForeignKey(
        InstrumentExpression,
        on_delete=models.CASCADE,
        related_name='manifestations',
        null=True,
        blank=True,
        verbose_name='نسخه سند'
    )
    publication_date = models.DateField(verbose_name='تاریخ انتشار')
    official_gazette_name = models.CharField(max_length=200, blank=True, verbose_name='نام روزنامه رسمی')
    gazette_issue_no = models.CharField(max_length=50, blank=True, verbose_name='شماره نامه')
    page_start = models.PositiveIntegerField(null=True, blank=True, verbose_name='صفحه شروع-پایان')
    source_url = models.URLField(blank=True, verbose_name='ELI URI / URL منبع')
    checksum_sha256 = models.CharField(max_length=64, unique=True, blank=True, verbose_name='چکسام SHA256')
    in_force_from = models.DateField(null=True, blank=True, verbose_name='اجرا از تاریخ')
    repeal_status = models.CharField(
        max_length=20,
        choices=RepealStatus.choices,
        default=RepealStatus.IN_FORCE,
        verbose_name='وضعیت سند'
    )
    in_force_to = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='اجرا تا تاریخ',
        help_text='در صورتی که وضعیت سند "لغو یا منسوخ شده" باشد، این فیلد الزامی است.'
    )
    retrieval_date = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ بازیابی')
    
    def clean(self):
        super().clean()
        if self.repeal_status == self.RepealStatus.REPEALED and not self.in_force_to:
            raise ValidationError({
                'in_force_to': 'برای اسناد لغو شده، تعیین تاریخ پایان اجرا الزامی است.'
            })
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.expr.work.title_official} - {self.publication_date}"



class LegalUnit(MPTTModel, BaseModel):
    """Hierarchical units within legal documents using MPTT."""
    # New FRBR references
    work = models.ForeignKey(
        'InstrumentWork',
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name='سند حقوقی',
        null=True,
        blank=True,
        help_text='مرجع به سند حقوقی اصلی (FRBR Work)'
    )
    expr = models.ForeignKey(
        'InstrumentExpression',
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name='نسخه سند',
        null=True,
        blank=True,
        help_text='مرجع به نسخه سند (FRBR Expression)'
    )
    manifestation = models.ForeignKey(
        'InstrumentManifestation',
        on_delete=models.SET_NULL,
        related_name='units',
        verbose_name='انتشار سند',
        null=True,
        blank=True
    )
    
    parent = TreeForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name='والد'
    )
    unit_type = models.CharField(
        max_length=20, 
        choices=UnitType.choices,
        verbose_name='نوع واحد'
    )
    label = models.CharField(max_length=100, verbose_name='برچسب')  # e.g., "ماده ۱۲"
    number = models.CharField(max_length=50, blank=True, verbose_name='شماره')
    order_index = models.PositiveIntegerField(default=0, verbose_name='ترتیب')
    path_label = models.CharField(max_length=500, blank=True, verbose_name='مسیر کامل')
    content = models.TextField(verbose_name='محتوا')
    
    # New Akoma Ntoso identifiers
    eli_fragment = models.CharField(max_length=200, blank=True, verbose_name='ELI Fragment')
    xml_id = models.CharField(max_length=100, blank=True, verbose_name='XML ID')
    
    # Many-to-many relationship with VocabularyTerm through intermediate model
    vocabulary_terms = models.ManyToManyField(
        'masterdata.VocabularyTerm',
        through='LegalUnitVocabularyTerm',
        blank=True,
        related_name='legal_units',
        verbose_name='برچسب‌ها'
    )
    
    history = HistoricalRecords(excluded_fields=['lft', 'rght', 'tree_id', 'level'])

    class MPTTMeta:
        order_insertion_by = ['order_index']

    class Meta:
        verbose_name = 'جزء سند حقوقی'
        verbose_name_plural = 'اجزاء سند حقوقی'
        ordering = ['tree_id', 'lft']

    def __str__(self):
        ref = self.work.title_official if self.work else 'بدون مرجع'
        return f"{ref} - {self.label}"

    def save(self, *args, **kwargs):
        # Auto-generate path_label
        if self.parent:
            self.path_label = f"{self.parent.path_label} > {self.label}"
        else:
            self.path_label = self.label
        super().save(*args, **kwargs)

    @property
    def is_editable(self):
        """Units are editable by default (document model removed)."""
        return True


class FileAsset(BaseModel):
    """File attachments for documents and units."""
    
    # FRBR references
    legal_unit = models.ForeignKey(
        LegalUnit, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='files',
        verbose_name='جزء سند حقوقی',
        help_text='مرجع به جزء سند حقوقی'
    )
    
    manifestation = models.ForeignKey(
        'InstrumentManifestation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='files',
        verbose_name='انتشار سند',
        help_text='مرجع به انتشار سند (FRBR Manifestation)'
    )
    
    # File metadata
    bucket = models.CharField(max_length=100, verbose_name='سطل', default='advisor-docs')
    object_key = models.CharField(max_length=500, verbose_name='مسیر فایل', blank=True)
    original_filename = models.CharField(max_length=255, verbose_name='نام فایل اصلی', blank=True)
    content_type = models.CharField(max_length=100, verbose_name='نوع فایل', blank=True)
    size_bytes = models.PositiveBigIntegerField(verbose_name='حجم فایل (بایت)', default=0)
    sha256 = models.CharField(max_length=64, verbose_name='اثر انگشت فایل', blank=True)
    
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='uploaded_files',
        verbose_name='آپلودکننده'
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'فایل ضمیمه'
        verbose_name_plural = 'فایل‌های ضمیمه'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} ({self.content_type})"

    def clean(self):
        from django.core.exceptions import ValidationError
        refs = [self.legal_unit, self.manifestation]
        active_refs = [ref for ref in refs if ref is not None]
        
        if len(active_refs) == 0:
            raise ValidationError('فایل باید به جزء سند حقوقی یا انتشار سند متصل باشد.')
        if len(active_refs) > 1:
            raise ValidationError('فایل نمی‌تواند همزمان به بیش از یک مرجع متصل باشد.')
    
    def get_file_url(self):
        """Generate a presigned URL for file access"""
        if not self.object_key:
            return None
        
        try:
            import boto3
            from django.conf import settings
            from botocore.config import Config
            
            # Create MinIO client
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
            
            # Generate presigned URL (valid for 1 hour)
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': self.object_key},
                ExpiresIn=3600
            )
            return url
        except Exception:
            # Fallback to direct URL
            from django.conf import settings
            return f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{self.object_key}"


# Relations and Citations Models

class InstrumentRelation(BaseModel):
    """Relations between FRBR Works (e.g., amendments, repeals, references)."""
    from_work = models.ForeignKey(
        'InstrumentWork',
        on_delete=models.CASCADE,
        related_name='outgoing_relations',
        verbose_name='اثر مبدأ'
    )
    to_work = models.ForeignKey(
        'InstrumentWork',
        on_delete=models.CASCADE,
        related_name='incoming_relations',
        verbose_name='اثر مقصد'
    )
    relation_type = models.CharField(
        max_length=30,
        choices=[
            ('amends', 'اصلاح می‌کند'),
            ('repeals', 'لغو می‌کند'),
            ('references', 'ارجاع می‌دهد'),
            ('implements', 'اجرا می‌کند'),
            ('derives_from', 'مشتق از'),
            ('supersedes', 'جایگزین می‌شود'),
        ],
        verbose_name='نوع رابطه'
    )
    effective_date = models.DateField(null=True, blank=True, verbose_name='تاریخ اثر')
    notes = models.TextField(blank=True, verbose_name='یادداشت‌ها')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'رابطه ابزار حقوقی'
        verbose_name_plural = 'ارتباط اسناد حقوقی'
        unique_together = ['from_work', 'to_work', 'relation_type']

    def __str__(self):
        return f"{self.from_work.title_official} {self.get_relation_type_display()} {self.to_work.title_official}"


class PinpointCitation(BaseModel):
    """Precise citations between specific units of legal documents."""
    from_unit = models.ForeignKey(
        'LegalUnit',
        on_delete=models.CASCADE,
        related_name='outgoing_citations',
        verbose_name='سند مبدأ'
    )
    to_unit = models.ForeignKey(
        'LegalUnit',
        on_delete=models.CASCADE,
        related_name='incoming_citations',
        verbose_name='سند اشاره شده'
    )
    citation_type = models.CharField(
        max_length=20,
        choices=[
            ('direct', 'ارجاع مستقیم'),
            ('see_also', 'نگاه کنید به'),
            ('cf', 'مقایسه کنید'),
            ('but_see', 'اما نگاه کنید'),
            ('contra', 'در تضاد با'),
        ],
        default='direct',
        verbose_name='نوع ارجاع'
    )
    context_text = models.TextField(blank=True, verbose_name='متن زمینه')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'ارجاع دقیق'
        verbose_name_plural = 'ارجاعات دقیق'

    def __str__(self):
        return f"{self.from_unit.path_label} → {self.to_unit.path_label}"


class LegalUnitVocabularyTerm(BaseModel):
    """Through model for LegalUnit-VocabularyTerm relationship with weight."""
    legal_unit = models.ForeignKey(
        'LegalUnit',
        on_delete=models.CASCADE,
        related_name='unit_vocabulary_terms',
        verbose_name='جزء سند'
    )
    vocabulary_term = models.ForeignKey(
        'masterdata.VocabularyTerm',
        on_delete=models.CASCADE,
        related_name='unit_vocabulary_terms',
        verbose_name='واژه'
    )
    weight = models.PositiveSmallIntegerField(
        default=5,
        help_text='وزن ارتباط (1 تا 10)',
        verbose_name='وزن'
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'برچسب جزء سند'
        verbose_name_plural = 'برچسب‌های اجزاء سند'
        unique_together = ['legal_unit', 'vocabulary_term']

    def __str__(self):
        return f"{self.legal_unit.label} - {self.vocabulary_term.term} (وزن: {self.weight})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.weight < 1 or self.weight > 10:
            raise ValidationError('وزن باید بین 1 تا 10 باشد.')




# Ingest and RAG Models

class IngestLog(BaseModel):
    """Log of data ingestion operations."""
    operation_type = models.CharField(
        max_length=20,
        choices=[
            ('create', 'ایجاد'),
            ('update', 'به‌روزرسانی'),
            ('delete', 'حذف'),
            ('bulk_import', 'واردات انبوه'),
            ('sync', 'همگام‌سازی'),
        ],
        verbose_name='نوع عملیات'
    )
    source_system = models.CharField(max_length=50, verbose_name='سیستم مبدأ', default='manual')
    source_id = models.CharField(max_length=100, blank=True, verbose_name='شناسه مبدأ')
    
    # Target object references
    target_work = models.ForeignKey(
        'InstrumentWork',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingest_logs',
        verbose_name='اثر هدف'
    )
    target_expression = models.ForeignKey(
        'InstrumentExpression',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingest_logs',
        verbose_name='بیان هدف'
    )
    target_manifestation = models.ForeignKey(
        'InstrumentManifestation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingest_logs',
        verbose_name='تجلی هدف'
    )
    
    # Operation details
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'در انتظار'),
            ('processing', 'در حال پردازش'),
            ('success', 'موفق'),
            ('failed', 'ناموفق'),
            ('partial', 'جزئی'),
        ],
        default='pending',
        verbose_name='وضعیت'
    )
    records_processed = models.PositiveIntegerField(default=0, verbose_name='رکوردهای پردازش‌شده')
    records_failed = models.PositiveIntegerField(default=0, verbose_name='رکوردهای ناموفق')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='متادیتا')
    
    started_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='started_ingests',
        null=True,
        blank=True,
        verbose_name='آغازکننده'
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تکمیل')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'گزارش ورود داده'
        verbose_name_plural = 'گزارش‌های ورود داده'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.source_system} ({self.get_status_display()})"


class Chunk(BaseModel):
    """Text chunks for embedding and retrieval."""
    expr = models.ForeignKey(
        'InstrumentExpression',
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name='نسخه سند'
    )
    unit = models.ForeignKey(
        'LegalUnit',
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name='واحد حقوقی'
    )
    
    chunk_text = models.TextField(verbose_name='متن چانک')
    token_count = models.PositiveIntegerField(verbose_name='تعداد توکن')
    overlap_prev = models.PositiveIntegerField(default=0, verbose_name='همپوشانی با قبلی')
    citation_payload_json = models.JSONField(verbose_name='اطلاعات ارجاع')
    hash = models.CharField(max_length=64, verbose_name='هش SHA-256')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'چانک متن'
        verbose_name_plural = 'چانک‌های متن'
        ordering = ['expr', 'unit', 'id']
        unique_together = ['expr', 'hash']

    def __str__(self):
        return f"{self.unit.label} - چانک {self.token_count} توکن"


class ChunkEmbedding(BaseModel):
    """Embeddings for text chunks."""
    chunk = models.ForeignKey(
        'Chunk',
        on_delete=models.CASCADE,
        related_name='embeddings',
        verbose_name='چانک'
    )
    embedding = models.JSONField(verbose_name='بردار تعبیه')  # Will store vector as JSON array
    model = models.CharField(max_length=100, verbose_name='مدل تعبیه')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'تعبیه چانک'
        verbose_name_plural = 'تعبیه‌های چانک'
        ordering = ['chunk', 'created_at']

    def __str__(self):
        return f"تعبیه {self.chunk} - {self.model}"


class QAEntry(BaseModel):
    """Question and Answer entries for legal content."""
    question = models.TextField(verbose_name='سؤال')
    answer = models.TextField(verbose_name='پاسخ')
    
    tags = models.ManyToManyField(
        VocabularyTerm, 
        blank=True, 
        related_name='qa_entries',
        verbose_name='برچسب‌ها'
    )
    
    # Source references
    source_unit = models.ForeignKey(
        LegalUnit, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='qa_entries',
        verbose_name='واحد مرجع'
    )
    
    # Status and workflow
    status = models.CharField(
        max_length=20, 
        choices=QAStatus.choices, 
        default=QAStatus.DRAFT,
        verbose_name='وضعیت'
    )
    
    # Workflow users
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_qa_entries',
        verbose_name='ایجادکننده'
    )
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_qa_entries',
        verbose_name='بازبین'
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_qa_entries',
        verbose_name='تأییدکننده'
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'پرسش و پاسخ'
        verbose_name_plural = 'پرسش و پاسخ‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f"Q: {self.question[:50]}..."

    @property
    def is_editable(self):
        """Check if QA entry can be edited."""
        return self.status in [QAStatus.DRAFT, QAStatus.UNDER_REVIEW]

    @property
    def is_approved(self):
        """Check if QA entry is approved."""
        return self.status == QAStatus.APPROVED
