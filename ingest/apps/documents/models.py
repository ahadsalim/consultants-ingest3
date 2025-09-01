import uuid
import hashlib
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.storage import default_storage
from mptt.models import MPTTModel, TreeForeignKey
from simple_history.models import HistoricalRecords

from ingest.apps.masterdata.models import BaseModel, Jurisdiction, IssuingAuthority, VocabularyTerm
from .enums import DocumentType, DocumentStatus, RelationType, UnitType, QAStatus


# FRBR Core Models - New Schema
class InstrumentWork(BaseModel):
    """FRBR Work level - abstract legal instrument concept."""
    
    class Meta:
        verbose_name = "اثر حقوقی"
        verbose_name_plural = "آثار حقوقی"
        
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
    eli_uri_work = models.URLField(blank=True, verbose_name='ELI URI اثر')
    urn_lex = models.CharField(max_length=200, blank=True, verbose_name='URN LEX')
    local_slug = models.SlugField(max_length=100, unique=True, verbose_name='شناسه محلی')
    primary_language = models.CharField(max_length=10, default='fa', verbose_name='زبان اصلی')
    subject_summary = models.TextField(blank=True, verbose_name='خلاصه موضوع')
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.title_official} ({self.get_doc_type_display()})"


class InstrumentExpression(BaseModel):
    """FRBR Expression level - specific language/version of a work."""
    
    class Meta:
        verbose_name = "بیان حقوقی"
        verbose_name_plural = "بیان‌های حقوقی"
        unique_together = ['work', 'language', 'consolidation_level', 'expression_date']
        
    work = models.ForeignKey(
        InstrumentWork,
        on_delete=models.CASCADE,
        related_name='expressions',
        verbose_name='اثر'
    )
    language = models.CharField(max_length=10, default='fa', verbose_name='زبان')
    consolidation_level = models.CharField(max_length=50, blank=True, verbose_name='سطح تلفیق')
    expression_date = models.DateField(verbose_name='تاریخ بیان')
    eli_uri_expr = models.URLField(blank=True, verbose_name='ELI URI بیان')
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.work.title_official} - {self.language} ({self.expression_date})"


class InstrumentManifestation(BaseModel):
    """FRBR Manifestation level - physical/digital embodiment."""
    
    class Meta:
        verbose_name = "تجلی حقوقی"
        verbose_name_plural = "تجلی‌های حقوقی"
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
        verbose_name='بیان'
    )
    publication_date = models.DateField(verbose_name='تاریخ انتشار')
    official_gazette_name = models.CharField(max_length=200, blank=True, verbose_name='نام روزنامه رسمی')
    gazette_issue_no = models.CharField(max_length=50, blank=True, verbose_name='شماره نشریه')
    page_start = models.PositiveIntegerField(null=True, blank=True, verbose_name='صفحه شروع')
    page_end = models.PositiveIntegerField(null=True, blank=True, verbose_name='صفحه پایان')
    source_url = models.URLField(blank=True, verbose_name='URL منبع')
    checksum_sha256 = models.CharField(max_length=64, unique=True, blank=True, verbose_name='چکسام SHA256')
    eli_uri_manifestation = models.URLField(blank=True, verbose_name='ELI URI تجلی')
    in_force_from = models.DateField(null=True, blank=True, verbose_name='اجرا از تاریخ')
    in_force_to = models.DateField(null=True, blank=True, verbose_name='اجرا تا تاریخ')
    repeal_status = models.CharField(max_length=50, blank=True, verbose_name='وضعیت لغو')
    retrieval_date = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ بازیابی')
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.expr.work.title_official} - {self.publication_date}"


class LegalDocument(BaseModel):
    """Legal document model with full lifecycle management."""
    
    class Meta:
        verbose_name = "سند حقوقی"
        verbose_name_plural = "📄 اسناد حقوقی"
    title = models.CharField(max_length=500, verbose_name='عنوان')
    reference_no = models.CharField(max_length=100, blank=True, verbose_name='شماره مرجع')
    doc_type = models.CharField(
        max_length=20, 
        choices=DocumentType.choices, 
        default=DocumentType.LAW,
        verbose_name='نوع سند'
    )
    jurisdiction = models.ForeignKey(
        Jurisdiction, 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name='حوزه قضایی'
    )
    authority = models.ForeignKey(
        IssuingAuthority, 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name='مرجع صادرکننده'
    )
    
    # Dates
    enactment_date = models.DateField(null=True, blank=True, verbose_name='تاریخ تصویب')
    effective_date = models.DateField(null=True, blank=True, verbose_name='تاریخ اجرا')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='تاریخ انقضا')
    
    # Status and workflow
    status = models.CharField(
        max_length=20, 
        choices=DocumentStatus.choices, 
        default=DocumentStatus.DRAFT,
        verbose_name='وضعیت'
    )
    
    # Relations
    subject_terms = models.ManyToManyField(
        VocabularyTerm, 
        blank=True, 
        related_name='documents',
        verbose_name='موضوعات'
    )
    
    # Workflow users
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_documents',
        verbose_name='ایجادکننده'
    )
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_documents',
        verbose_name='بازبین'
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_documents',
        verbose_name='تأییدکننده'
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'سند حقوقی'
        verbose_name_plural = 'اسناد حقوقی'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"

    @property
    def is_editable(self):
        """Check if document can be edited."""
        return self.status in [DocumentStatus.DRAFT, DocumentStatus.UNDER_REVIEW]

    @property
    def is_approved(self):
        """Check if document is approved."""
        return self.status == DocumentStatus.APPROVED


class DocumentRelation(BaseModel):
    """Relations between legal documents."""
    from_document = models.ForeignKey(
        LegalDocument, 
        on_delete=models.CASCADE, 
        related_name='outgoing_relations',
        verbose_name='سند مبدأ'
    )
    to_document = models.ForeignKey(
        LegalDocument, 
        on_delete=models.CASCADE, 
        related_name='incoming_relations',
        verbose_name='سند مقصد'
    )
    relation_type = models.CharField(
        max_length=20, 
        choices=RelationType.choices,
        verbose_name='نوع رابطه'
    )
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'رابطه اسناد'
        verbose_name_plural = 'روابط اسناد'
        unique_together = ['from_document', 'to_document', 'relation_type']

    def __str__(self):
        return f"{self.from_document.title} {self.get_relation_type_display()} {self.to_document.title}"


class LegalUnit(MPTTModel, BaseModel):
    """Hierarchical units within legal documents using MPTT."""
    # Legacy reference (keep for backward compatibility)
    document = models.ForeignKey(
        LegalDocument, 
        on_delete=models.CASCADE, 
        related_name='units',
        verbose_name='سند',
        null=True,
        blank=True
    )
    
    # New FRBR references
    work = models.ForeignKey(
        'InstrumentWork',
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name='اثر',
        null=True,
        blank=True
    )
    expr = models.ForeignKey(
        'InstrumentExpression',
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name='بیان',
        null=True,
        blank=True
    )
    manifestation = models.ForeignKey(
        'InstrumentManifestation',
        on_delete=models.SET_NULL,
        related_name='units',
        verbose_name='تجلی',
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
    text_plain = models.TextField(blank=True, verbose_name='متن ساده')
    
    history = HistoricalRecords(excluded_fields=['lft', 'rght', 'tree_id', 'level'])

    class MPTTMeta:
        order_insertion_by = ['order_index']

    class Meta:
        verbose_name = 'واحد حقوقی'
        verbose_name_plural = 'واحدهای حقوقی'
        ordering = ['document', 'tree_id', 'lft']
        constraints = [
            models.CheckConstraint(
                check=models.Q(document__isnull=False) | models.Q(work__isnull=False),
                name='legalunit_has_document_or_work'
            )
        ]

    def __str__(self):
        return f"{self.document.title} - {self.label}"

    def save(self, *args, **kwargs):
        # Auto-generate path_label
        if self.parent:
            self.path_label = f"{self.parent.path_label} > {self.label}"
        else:
            self.path_label = self.label
        super().save(*args, **kwargs)

    @property
    def is_editable(self):
        """Check if unit can be edited based on document status."""
        return self.document.is_editable


class FileAsset(BaseModel):
    """File attachments for documents and units."""
    # Legacy references (keep for backward compatibility)
    document = models.ForeignKey(
        LegalDocument, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='files',
        verbose_name='سند'
    )
    legal_unit = models.ForeignKey(
        LegalUnit, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='files',
        verbose_name='واحد حقوقی'
    )
    
    # New FRBR reference - files primarily belong to manifestations
    manifestation = models.ForeignKey(
        'InstrumentManifestation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='files',
        verbose_name='تجلی'
    )
    
    # File metadata
    bucket = models.CharField(max_length=100, verbose_name='سطل')
    object_key = models.CharField(max_length=500, verbose_name='کلید شیء')
    original_filename = models.CharField(max_length=255, verbose_name='نام فایل اصلی')
    content_type = models.CharField(max_length=100, verbose_name='نوع محتوا')
    size_bytes = models.PositiveBigIntegerField(verbose_name='اندازه (بایت)')
    sha256 = models.CharField(max_length=64, verbose_name='هش SHA256')
    
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
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(document__isnull=False) | 
                    models.Q(legal_unit__isnull=False) |
                    models.Q(manifestation__isnull=False)
                ),
                name='fileasset_has_reference'
            )
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.content_type})"

    def clean(self):
        from django.core.exceptions import ValidationError
        refs = [self.document, self.legal_unit, self.manifestation]
        active_refs = [ref for ref in refs if ref is not None]
        
        if len(active_refs) == 0:
            raise ValidationError('فایل باید به سند، واحد حقوقی، یا تجلی متصل باشد.')
        if len(active_refs) > 1:
            raise ValidationError('فایل نمی‌تواند همزمان به بیش از یک مرجع متصل باشد.')


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
        verbose_name_plural = 'روابط ابزارهای حقوقی'
        unique_together = ['from_work', 'to_work', 'relation_type']

    def __str__(self):
        return f"{self.from_work.title_official} {self.get_relation_type_display()} {self.to_work.title_official}"


class PinpointCitation(BaseModel):
    """Precise citations between specific units of legal documents."""
    from_unit = models.ForeignKey(
        'LegalUnit',
        on_delete=models.CASCADE,
        related_name='outgoing_citations',
        verbose_name='واحد مبدأ'
    )
    to_unit = models.ForeignKey(
        'LegalUnit',
        on_delete=models.CASCADE,
        related_name='incoming_citations',
        verbose_name='واحد مقصد'
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
    start_offset = models.PositiveIntegerField(null=True, blank=True, verbose_name='آفست شروع')
    end_offset = models.PositiveIntegerField(null=True, blank=True, verbose_name='آفست پایان')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'ارجاع دقیق'
        verbose_name_plural = 'ارجاعات دقیق'

    def __str__(self):
        return f"{self.from_unit.path_label} → {self.to_unit.path_label}"


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
    source_document = models.ForeignKey(
        LegalDocument, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='qa_entries',
        verbose_name='سند مرجع'
    )
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
