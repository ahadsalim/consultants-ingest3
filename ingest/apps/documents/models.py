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


class LegalDocument(BaseModel):
    """Legal document model with full lifecycle management."""
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
    document = models.ForeignKey(
        LegalDocument, 
        on_delete=models.CASCADE, 
        related_name='units',
        verbose_name='سند'
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
    
    history = HistoricalRecords()

    class MPTTMeta:
        order_insertion_by = ['order_index']

    class Meta:
        verbose_name = 'واحد حقوقی'
        verbose_name_plural = 'واحدهای حقوقی'
        ordering = ['document', 'tree_id', 'lft']

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

    def __str__(self):
        return f"{self.original_filename} ({self.content_type})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.document and not self.legal_unit:
            raise ValidationError('فایل باید به سند یا واحد حقوقی متصل باشد.')
        if self.document and self.legal_unit:
            raise ValidationError('فایل نمی‌تواند همزمان به سند و واحد حقوقی متصل باشد.')


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
