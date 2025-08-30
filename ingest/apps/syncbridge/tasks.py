import json
import requests
from typing import Dict, Any
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import SyncJob, SyncJobStatus, SyncJobType
from ingest.apps.documents.models import LegalDocument, LegalUnit, QAEntry
from ingest.apps.masterdata.models import Jurisdiction, IssuingAuthority, Vocabulary, VocabularyTerm
from ingest.common.s3 import generate_presigned_url


@shared_task(bind=True, max_retries=3)
def process_sync_job(self, job_id: str):
    """Process a sync job to send data to core service."""
    try:
        job = SyncJob.objects.get(id=job_id)
        job.mark_running()
        
        # Build payload based on job type
        payload = build_payload(job.job_type, job.target_id)
        
        # Send to core service
        response = send_to_core(payload)
        
        if response.status_code == 200:
            job.mark_success()
        else:
            error_msg = f"Core service returned {response.status_code}: {response.text}"
            job.mark_error(error_msg)
            
    except SyncJob.DoesNotExist:
        return f"SyncJob {job_id} not found"
    except Exception as exc:
        job.mark_error(str(exc))
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def build_payload(job_type: str, target_id: str) -> Dict[str, Any]:
    """Build payload for different entity types."""
    
    if job_type == SyncJobType.DOCUMENT:
        return build_document_payload(target_id)
    elif job_type == SyncJobType.UNIT:
        return build_unit_payload(target_id)
    elif job_type == SyncJobType.QA:
        return build_qa_payload(target_id)
    elif job_type == SyncJobType.JURISDICTION:
        return build_jurisdiction_payload(target_id)
    elif job_type == SyncJobType.AUTHORITY:
        return build_authority_payload(target_id)
    elif job_type == SyncJobType.VOCABULARY:
        return build_vocabulary_payload(target_id)
    else:
        raise ValueError(f"Unknown job type: {job_type}")


def build_document_payload(document_id: str) -> Dict[str, Any]:
    """Build payload for legal document."""
    doc = LegalDocument.objects.select_related(
        'jurisdiction', 'authority', 'created_by', 'reviewed_by', 'approved_by'
    ).prefetch_related(
        'subject_terms', 'units', 'files', 'outgoing_relations__to_document'
    ).get(id=document_id)
    
    return {
        "type": "legal_document",
        "id": str(doc.id),
        "title": doc.title,
        "reference_no": doc.reference_no,
        "doc_type": doc.doc_type,
        "jurisdiction": {
            "id": str(doc.jurisdiction.id),
            "name": doc.jurisdiction.name,
            "code": doc.jurisdiction.code
        },
        "authority": {
            "id": str(doc.authority.id),
            "name": doc.authority.name,
            "code": doc.authority.code
        },
        "dates": {
            "enactment": doc.enactment_date.isoformat() if doc.enactment_date else None,
            "effective": doc.effective_date.isoformat() if doc.effective_date else None,
            "expiry": doc.expiry_date.isoformat() if doc.expiry_date else None
        },
        "status": doc.status,
        "subject_terms": [
            {
                "id": str(term.id),
                "term": term.term,
                "code": term.code,
                "vocabulary": term.vocabulary.name
            }
            for term in doc.subject_terms.all()
        ],
        "relations": [
            {
                "to_id": str(rel.to_document.id),
                "relation_type": rel.relation_type
            }
            for rel in doc.outgoing_relations.all()
        ],
        "units": [
            {
                "id": str(unit.id),
                "label": unit.label,
                "number": unit.number,
                "path_label": unit.path_label,
                "order_index": unit.order_index,
                "unit_type": unit.unit_type,
                "content": unit.content,
                "parent_id": str(unit.parent.id) if unit.parent else None
            }
            for unit in doc.units.all()
        ],
        "files": [
            {
                "id": str(file_asset.id),
                "filename": file_asset.original_filename,
                "content_type": file_asset.content_type,
                "size_bytes": file_asset.size_bytes,
                "sha256": file_asset.sha256,
                "url": generate_presigned_url(file_asset.bucket, file_asset.object_key, expires_in=3600)
            }
            for file_asset in doc.files.all()
        ],
        "workflow": {
            "created_by": doc.created_by.username,
            "reviewed_by": doc.reviewed_by.username if doc.reviewed_by else None,
            "approved_by": doc.approved_by.username if doc.approved_by else None,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        }
    }


def build_qa_payload(qa_id: str) -> Dict[str, Any]:
    """Build payload for QA entry."""
    qa = QAEntry.objects.select_related(
        'source_document', 'source_unit', 'created_by', 'reviewed_by', 'approved_by'
    ).prefetch_related('tags').get(id=qa_id)
    
    return {
        "type": "qa_entry",
        "id": str(qa.id),
        "question": qa.question,
        "answer": qa.answer,
        "status": qa.status,
        "tags": [
            {
                "id": str(tag.id),
                "term": tag.term,
                "code": tag.code,
                "vocabulary": tag.vocabulary.name
            }
            for tag in qa.tags.all()
        ],
        "source": {
            "document_id": str(qa.source_document.id) if qa.source_document else None,
            "unit_id": str(qa.source_unit.id) if qa.source_unit else None
        },
        "workflow": {
            "created_by": qa.created_by.username,
            "reviewed_by": qa.reviewed_by.username if qa.reviewed_by else None,
            "approved_by": qa.approved_by.username if qa.approved_by else None,
            "created_at": qa.created_at.isoformat(),
            "updated_at": qa.updated_at.isoformat()
        }
    }


def build_jurisdiction_payload(jurisdiction_id: str) -> Dict[str, Any]:
    """Build payload for jurisdiction."""
    jurisdiction = Jurisdiction.objects.get(id=jurisdiction_id)
    
    return {
        "type": "jurisdiction",
        "id": str(jurisdiction.id),
        "name": jurisdiction.name,
        "code": jurisdiction.code,
        "description": jurisdiction.description,
        "is_active": jurisdiction.is_active,
        "created_at": jurisdiction.created_at.isoformat(),
        "updated_at": jurisdiction.updated_at.isoformat()
    }


def build_authority_payload(authority_id: str) -> Dict[str, Any]:
    """Build payload for issuing authority."""
    authority = IssuingAuthority.objects.select_related('jurisdiction').get(id=authority_id)
    
    return {
        "type": "issuing_authority",
        "id": str(authority.id),
        "name": authority.name,
        "code": authority.code,
        "description": authority.description,
        "is_active": authority.is_active,
        "jurisdiction": {
            "id": str(authority.jurisdiction.id),
            "name": authority.jurisdiction.name,
            "code": authority.jurisdiction.code
        },
        "created_at": authority.created_at.isoformat(),
        "updated_at": authority.updated_at.isoformat()
    }


def build_vocabulary_payload(vocabulary_id: str) -> Dict[str, Any]:
    """Build payload for vocabulary."""
    vocabulary = Vocabulary.objects.prefetch_related('terms').get(id=vocabulary_id)
    
    return {
        "type": "vocabulary",
        "id": str(vocabulary.id),
        "name": vocabulary.name,
        "code": vocabulary.code,
        "description": vocabulary.description,
        "terms": [
            {
                "id": str(term.id),
                "term": term.term,
                "code": term.code,
                "description": term.description,
                "is_active": term.is_active
            }
            for term in vocabulary.terms.all()
        ],
        "created_at": vocabulary.created_at.isoformat(),
        "updated_at": vocabulary.updated_at.isoformat()
    }


def build_unit_payload(unit_id: str) -> Dict[str, Any]:
    """Build payload for legal unit."""
    unit = LegalUnit.objects.select_related('document', 'parent').get(id=unit_id)
    
    return {
        "type": "legal_unit",
        "id": str(unit.id),
        "document_id": str(unit.document.id),
        "parent_id": str(unit.parent.id) if unit.parent else None,
        "unit_type": unit.unit_type,
        "label": unit.label,
        "number": unit.number,
        "order_index": unit.order_index,
        "path_label": unit.path_label,
        "content": unit.content,
        "created_at": unit.created_at.isoformat(),
        "updated_at": unit.updated_at.isoformat()
    }


def send_to_core(payload: Dict[str, Any]) -> requests.Response:
    """Send payload to core service."""
    headers = {
        'Content-Type': 'application/json',
        'X-Bridge-Token': settings.CORE_TOKEN
    }
    
    url = f"{settings.CORE_BASE_URL}/sync/import"
    
    response = requests.post(
        url,
        data=json.dumps(payload, ensure_ascii=False),
        headers=headers,
        timeout=30
    )
    
    return response


def create_sync_job(job_type: str, target_id: str) -> SyncJob:
    """Create a new sync job."""
    # Build preview payload (limited data for display)
    try:
        payload = build_payload(job_type, target_id)
        preview = {
            "type": payload.get("type"),
            "id": payload.get("id"),
            "title": payload.get("title") or payload.get("name") or payload.get("question", "")[:100]
        }
    except Exception as e:
        preview = {"error": str(e)}
    
    job = SyncJob.objects.create(
        job_type=job_type,
        target_id=target_id,
        payload_preview=preview
    )
    
    # Queue the job
    process_sync_job.delay(str(job.id))
    
    return job
