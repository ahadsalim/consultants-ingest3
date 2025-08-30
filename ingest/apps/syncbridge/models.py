import uuid
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from ingest.apps.masterdata.models import BaseModel


class SyncJobStatus(models.TextChoices):
    PENDING = 'pending', 'در انتظار'
    RUNNING = 'running', 'در حال اجرا'
    SUCCESS = 'success', 'موفق'
    ERROR = 'error', 'خطا'


class SyncJobType(models.TextChoices):
    DOCUMENT = 'document', 'سند'
    UNIT = 'unit', 'واحد'
    QA = 'qa', 'پرسش و پاسخ'
    VOCABULARY = 'vocabulary', 'واژگان'
    AUTHORITY = 'authority', 'مرجع'
    JURISDICTION = 'jurisdiction', 'حوزه قضایی'


class SyncJob(BaseModel):
    """Sync jobs for sending data to core service."""
    job_type = models.CharField(
        max_length=20,
        choices=SyncJobType.choices,
        verbose_name='نوع کار'
    )
    target_id = models.UUIDField(verbose_name='شناسه هدف')
    payload_preview = models.JSONField(default=dict, verbose_name='پیش‌نمایش محتوا')
    status = models.CharField(
        max_length=20,
        choices=SyncJobStatus.choices,
        default=SyncJobStatus.PENDING,
        verbose_name='وضعیت'
    )
    last_error = models.TextField(blank=True, verbose_name='آخرین خطا')
    retry_count = models.PositiveIntegerField(default=0, verbose_name='تعداد تلاش مجدد')
    max_retries = models.PositiveIntegerField(default=3, verbose_name='حداکثر تلاش مجدد')
    next_retry_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تلاش بعدی')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان تکمیل')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'کار همگام‌سازی'
        verbose_name_plural = 'کارهای همگام‌سازی'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_job_type_display()} - {self.target_id} ({self.get_status_display()})"

    @property
    def can_retry(self):
        """Check if job can be retried."""
        return (
            self.status == SyncJobStatus.ERROR and 
            self.retry_count < self.max_retries
        )

    def mark_running(self):
        """Mark job as running."""
        self.status = SyncJobStatus.RUNNING
        self.save(update_fields=['status', 'updated_at'])

    def mark_success(self):
        """Mark job as successful."""
        self.status = SyncJobStatus.SUCCESS
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def mark_error(self, error_message: str):
        """Mark job as failed with error message."""
        self.status = SyncJobStatus.ERROR
        self.last_error = error_message
        self.retry_count += 1
        
        # Calculate next retry time with exponential backoff
        if self.can_retry:
            backoff_seconds = 2 ** self.retry_count * 60  # 2, 4, 8 minutes
            self.next_retry_at = timezone.now() + timezone.timedelta(seconds=backoff_seconds)
        
        self.save(update_fields=['status', 'last_error', 'retry_count', 'next_retry_at', 'updated_at'])
