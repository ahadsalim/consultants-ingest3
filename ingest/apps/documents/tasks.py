"""
Celery tasks for document processing and chunking.
"""
import logging
from celery import shared_task
from django.db import transaction

from .models import InstrumentExpression, LegalUnit
from .services import chunk_processing_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_expression_chunks(self, expression_id: str):
    """
    Process all legal units in an expression to create chunks and embeddings.
    
    Args:
        expression_id: UUID of the InstrumentExpression to process
    """
    try:
        expression = InstrumentExpression.objects.get(id=expression_id)
        logger.info(f"Starting chunk processing for expression {expression_id}")
        
        results = chunk_processing_service.process_expression(expression)
        
        logger.info(f"Completed chunk processing for expression {expression_id}: {results}")
        return results
        
    except InstrumentExpression.DoesNotExist:
        logger.error(f"Expression {expression_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error processing expression {expression_id}: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)


@shared_task(bind=True, max_retries=3)
def process_legal_unit_chunks(self, unit_id: str):
    """
    Process a single legal unit to create chunks and embeddings.
    
    Args:
        unit_id: UUID of the LegalUnit to process
    """
    try:
        unit = LegalUnit.objects.get(id=unit_id)
        logger.info(f"Starting chunk processing for legal unit {unit_id}")
        
        results = chunk_processing_service.process_legal_unit(unit)
        
        logger.info(f"Completed chunk processing for legal unit {unit_id}: {results}")
        return results
        
    except LegalUnit.DoesNotExist:
        logger.error(f"Legal unit {unit_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error processing legal unit {unit_id}: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)


@shared_task
def cleanup_duplicate_chunks():
    """
    Cleanup task to remove duplicate chunks based on hash.
    """
    from django.db.models import Count
    from .models import Chunk
    
    # Find duplicate hashes
    duplicates = (
        Chunk.objects
        .values('expr', 'hash')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    
    deleted_count = 0
    for duplicate in duplicates:
        # Keep the first chunk, delete the rest
        chunks = Chunk.objects.filter(
            expr=duplicate['expr'],
            hash=duplicate['hash']
        ).order_by('created_at')
        
        for chunk in chunks[1:]:  # Skip the first one
            chunk.delete()
            deleted_count += 1
    
    logger.info(f"Cleaned up {deleted_count} duplicate chunks")
    return {'deleted_count': deleted_count}
