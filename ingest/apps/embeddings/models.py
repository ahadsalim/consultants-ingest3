import uuid
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings
from pgvector.django import VectorField
from simple_history.models import HistoricalRecords

from ingest.apps.masterdata.models import BaseModel


class Embedding(BaseModel):
    """Store vector embeddings for content with pgvector."""
    
    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Embedding data
    model_name = models.CharField(max_length=100, verbose_name='نام مدل')
    vector = VectorField(dimensions=settings.EMBEDDING_DIMENSION, verbose_name='بردار')
    
    # Metadata
    text_content = models.TextField(verbose_name='محتوای متنی')  # Store original text for reference
    
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'جاسازی'
        verbose_name_plural = 'جاسازی‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['model_name']),
        ]

    def __str__(self):
        return f"{self.content_object} - {self.model_name}"

    @classmethod
    def search_similar(cls, query_vector, model_name: str = None, limit: int = 10):
        """Search for similar embeddings using cosine similarity."""
        from django.db import connection
        
        qs = cls.objects.all()
        if model_name:
            qs = qs.filter(model_name=model_name)
        
        # Use pgvector's cosine distance operator
        qs = qs.extra(
            select={'similarity': '1 - (vector <=> %s)'},
            select_params=[query_vector],
            order_by=['-similarity']
        )[:limit]
        
        return qs
