"""
Django signals for automatic chunk processing.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from .models import LegalUnit, InstrumentExpression
from .tasks import process_expression_chunks

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LegalUnit)
def trigger_chunk_processing_on_legal_unit_save(sender, instance, created, **kwargs):
    """
    Trigger chunk processing when legal units are created or updated.
    
    This signal fires after a LegalUnit is saved and schedules chunk processing
    for the entire expression if this is a new unit or if content has changed.
    """
    if created or (hasattr(instance, '_content_changed') and instance._content_changed):
        if instance.expr:
            # Use transaction.on_commit to ensure the LegalUnit is fully saved
            # before triggering the async task
            transaction.on_commit(
                lambda: process_expression_chunks.delay(str(instance.expr.id))
            )
            logger.info(f"Scheduled chunk processing for expression {instance.expr.id} due to LegalUnit {instance.id}")


@receiver(post_save, sender=InstrumentExpression)
def trigger_chunk_processing_on_expression_save(sender, instance, created, **kwargs):
    """
    Trigger chunk processing when an InstrumentExpression is created.
    
    This ensures that when a new expression is created, all its legal units
    will be processed for chunking and embedding.
    """
    if created:
        # Check if this expression has any legal units
        if instance.units.exists():
            transaction.on_commit(
                lambda: process_expression_chunks.delay(str(instance.id))
            )
            logger.info(f"Scheduled chunk processing for new expression {instance.id}")


@receiver(post_delete, sender=LegalUnit)
def cleanup_chunks_on_legal_unit_delete(sender, instance, **kwargs):
    """
    Clean up chunks when a legal unit is deleted.
    
    This signal ensures that when a LegalUnit is deleted, its associated
    chunks and embeddings are also removed from the database.
    """
    # Chunks will be automatically deleted due to CASCADE relationship
    # but we log this for monitoring purposes
    chunk_count = instance.chunks.count()
    if chunk_count > 0:
        logger.info(f"Deleted {chunk_count} chunks for LegalUnit {instance.id}")


# Custom signal for tracking content changes
def track_legal_unit_content_changes(sender, instance, **kwargs):
    """
    Track if the content field of a LegalUnit has changed.
    
    This is used by the post_save signal to determine if chunk processing
    should be triggered for existing units.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = LegalUnit.objects.get(pk=instance.pk)
            instance._content_changed = old_instance.content != instance.content
        except LegalUnit.DoesNotExist:
            instance._content_changed = False
    else:
        instance._content_changed = True  # New instance


# Connect the pre_save signal for content change tracking
from django.db.models.signals import pre_save
pre_save.connect(track_legal_unit_content_changes, sender=LegalUnit)
