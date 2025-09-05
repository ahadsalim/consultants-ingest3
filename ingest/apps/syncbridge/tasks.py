import json
import requests
from typing import Dict, Any
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import SyncJob, SyncJobStatus, SyncJobType
from ingest.apps.documents.models import (
    InstrumentWork, InstrumentExpression, InstrumentManifestation, LegalUnit, QAEntry
)
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


def build_document_payload(manifestation_id: str) -> Dict[str, Any]:
    """Build payload for a manifestation, representing the full document context."""
    manifestation = InstrumentManifestation.objects.select_related(
        'expr__work__jurisdiction', 'expr__work__authority', 'expr__lang'
    ).prefetch_related(
        'expr__work__tags', 'files'
    ).get(id=manifestation_id)
    
    work = manifestation.expr.work
    expr = manifestation.expr
    
    return {
        "type": "document_manifestation",
        "manifestation_id": str(manifestation.id),
        "expression_id": str(expr.id),
        "work_id": str(work.id),
        
        # Work details
        "title_official": work.title_official,
        "title_short": work.title_short,
        "work_type": work.work_type,
        "jurisdiction": {
            "id": str(work.jurisdiction.id),
            "name": work.jurisdiction.name,
        },
        "authority": {
            "id": str(work.authority.id),
            "name": work.authority.name,
        },
        "tags": [t.name for t in work.tags.all()],
        
        # Expression details
        "expression_lang": expr.lang.code,
        "expression_date": expr.expression_date.isoformat() if expr.expression_date else None,
        
        # Manifestation details
        "publication_date": manifestation.publication_date.isoformat() if manifestation.publication_date else None,
        "official_gazette_name": manifestation.official_gazette_name,
        "gazette_issue_no": manifestation.gazette_issue_no,
        "repeal_status": manifestation.repeal_status,
        "in_force_from": manifestation.in_force_from.isoformat() if manifestation.in_force_from else None,
        "in_force_to": manifestation.in_force_to.isoformat() if manifestation.in_force_to else None,
        "source_url": manifestation.source_url,
        
        "files": [
            {
                "id": str(f.id),
                "filename": f.original_filename,
                "content_type": f.content_type,
                "size_bytes": f.size_bytes,
                "sha256": f.sha256,
                "url": generate_presigned_url(f.bucket, f.object_key, expires_in=3600)
            }
            for f in manifestation.files.all()
        ],
        
        "created_at": manifestation.created_at.isoformat(),
        "updated_at": manifestation.updated_at.isoformat(),
    }


def build_qa_payload(qa_id: str) -> Dict[str, Any]:
    """Build payload for QA entry."""
    qa = QAEntry.objects.select_related(
        'source_unit', 'created_by', 'reviewed_by', 'approved_by'
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
    unit = LegalUnit.objects.select_related('work', 'expr', 'manifestation', 'parent').get(id=unit_id)
    
    return {
        "type": "legal_unit",
        "id": str(unit.id),
        "work_id": str(unit.work.id) if unit.work else None,
        "manifestation_id": str(unit.manifestation.id) if unit.manifestation else None,
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
