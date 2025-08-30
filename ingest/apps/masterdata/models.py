import uuid
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class BaseModel(models.Model):
    """Base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Jurisdiction(BaseModel):
    """Legal jurisdiction (e.g., Iran, Tehran Province)."""
    name = models.CharField(max_length=200, verbose_name='نام')
    code = models.CharField(max_length=50, unique=True, verbose_name='کد')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'حوزه قضایی'
        verbose_name_plural = 'حوزه‌های قضایی'
        ordering = ['name']

    def __str__(self):
        return self.name


class IssuingAuthority(BaseModel):
    """Authority that issues legal documents."""
    name = models.CharField(max_length=200, verbose_name='نام')
    code = models.CharField(max_length=50, unique=True, verbose_name='کد')
    jurisdiction = models.ForeignKey(
        Jurisdiction, 
        on_delete=models.CASCADE, 
        related_name='authorities',
        verbose_name='حوزه قضایی'
    )
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'مرجع صادرکننده'
        verbose_name_plural = 'مراجع صادرکننده'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.jurisdiction.name})"


class Vocabulary(BaseModel):
    """Vocabulary for categorizing terms."""
    name = models.CharField(max_length=200, verbose_name='نام')
    code = models.CharField(max_length=50, unique=True, verbose_name='کد')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'واژگان'
        verbose_name_plural = 'واژگان‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name


class VocabularyTerm(BaseModel):
    """Terms within a vocabulary."""
    vocabulary = models.ForeignKey(
        Vocabulary, 
        on_delete=models.CASCADE, 
        related_name='terms',
        verbose_name='واژگان'
    )
    term = models.CharField(max_length=200, verbose_name='اصطلاح')
    code = models.CharField(max_length=50, verbose_name='کد')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'اصطلاح واژگان'
        verbose_name_plural = 'اصطلاحات واژگان'
        ordering = ['vocabulary__name', 'term']
        unique_together = ['vocabulary', 'code']

    def __str__(self):
        return f"{self.vocabulary.name}: {self.term}"
