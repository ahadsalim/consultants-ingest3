import numpy as np
from celery import shared_task
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from .models import Embedding
from ingest.apps.documents.models import LegalDocument, LegalUnit, QAEntry


@shared_task
def generate_embedding(content_type_id: int, object_id: str, model_name: str = "stub"):
    """Generate embedding for a content object."""
    try:
        content_type = ContentType.objects.get(id=content_type_id)
        content_object = content_type.get_object_for_this_type(id=object_id)
        
        # Extract text content based on object type
        if isinstance(content_object, LegalDocument):
            text_content = f"{content_object.title} {content_object.reference_no or ''}"
        elif isinstance(content_object, LegalUnit):
            text_content = f"{content_object.label} {content_object.content}"
        elif isinstance(content_object, QAEntry):
            text_content = f"{content_object.question} {content_object.answer}"
        else:
            text_content = str(content_object)
        
        # Generate embedding vector (stub implementation)
        vector = generate_stub_embedding(text_content)
        
        # Store or update embedding
        embedding, created = Embedding.objects.update_or_create(
            content_type=content_type,
            object_id=object_id,
            model_name=model_name,
            defaults={
                'vector': vector,
                'text_content': text_content
            }
        )
        
        return f"Embedding {'created' if created else 'updated'} for {content_object}"
        
    except Exception as e:
        return f"Error generating embedding: {str(e)}"


def generate_stub_embedding(text: str) -> list:
    """
    Stub embedding generator that creates zero vectors.
    Replace this with actual embedding model when ready.
    """
    # For now, return zero vector of configured dimension
    dimension = settings.EMBEDDING_DIMENSION
    return [0.0] * dimension


def generate_real_embedding(text: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> list:
    """
    Real embedding generator using sentence transformers.
    Uncomment and install sentence-transformers when ready to use.
    """
    # from sentence_transformers import SentenceTransformer
    # 
    # model = SentenceTransformer(model_name)
    # embedding = model.encode(text)
    # return embedding.tolist()
    
    # For now, use stub
    return generate_stub_embedding(text)


@shared_task
def batch_generate_embeddings(model_name: str = "stub"):
    """Generate embeddings for all content that doesn't have them."""
    results = []
    
    # Process LegalDocuments
    for doc in LegalDocument.objects.filter(status='approved'):
        content_type = ContentType.objects.get_for_model(LegalDocument)
        if not Embedding.objects.filter(
            content_type=content_type, 
            object_id=doc.id, 
            model_name=model_name
        ).exists():
            result = generate_embedding.delay(content_type.id, str(doc.id), model_name)
            results.append(f"Queued embedding for document {doc.id}")
    
    # Process LegalUnits
    for unit in LegalUnit.objects.filter(document__status='approved'):
        content_type = ContentType.objects.get_for_model(LegalUnit)
        if not Embedding.objects.filter(
            content_type=content_type, 
            object_id=unit.id, 
            model_name=model_name
        ).exists():
            result = generate_embedding.delay(content_type.id, str(unit.id), model_name)
            results.append(f"Queued embedding for unit {unit.id}")
    
    # Process QAEntries
    for qa in QAEntry.objects.filter(status='approved'):
        content_type = ContentType.objects.get_for_model(QAEntry)
        if not Embedding.objects.filter(
            content_type=content_type, 
            object_id=qa.id, 
            model_name=model_name
        ).exists():
            result = generate_embedding.delay(content_type.id, str(qa.id), model_name)
            results.append(f"Queued embedding for QA {qa.id}")
    
    return results
