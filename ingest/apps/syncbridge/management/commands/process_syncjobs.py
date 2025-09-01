"""
Management command to process pending sync jobs without Celery.
"""
import logging
import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import models
import requests
from ingest.apps.syncbridge.models import SyncJob, SyncJobStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending sync jobs and send to core service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=50,
            help='Maximum number of jobs to process in one run'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending'
        )

    def handle(self, *args, **options):
        max_jobs = options['max_jobs']
        dry_run = options['dry_run']
        
        self.stdout.write(f"Processing sync jobs (max: {max_jobs}, dry-run: {dry_run})")
        
        # Get pending jobs and jobs ready for retry
        now = timezone.now()
        pending_jobs = SyncJob.objects.filter(
            status=SyncJobStatus.PENDING
        ).order_by('created_at')[:max_jobs]
        
        retry_jobs = SyncJob.objects.filter(
            status=SyncJobStatus.ERROR,
            next_retry_at__lte=now,
            retry_count__lt=models.F('max_retries')
        ).order_by('next_retry_at')[:max_jobs]
        
        all_jobs = list(pending_jobs) + list(retry_jobs)
        
        if not all_jobs:
            self.stdout.write(self.style.SUCCESS("No jobs to process"))
            return
            
        self.stdout.write(f"Found {len(all_jobs)} jobs to process")
        
        processed = 0
        succeeded = 0
        failed = 0
        
        for job in all_jobs:
            try:
                if dry_run:
                    self.stdout.write(f"[DRY-RUN] Would process: {job}")
                    continue
                    
                self.stdout.write(f"Processing job {job.id}: {job.job_type} -> {job.target_id}")
                
                # Mark as running
                job.mark_running()
                
                # Send to core service
                success = self._send_to_core(job)
                
                if success:
                    job.mark_success()
                    succeeded += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ Job {job.id} completed"))
                else:
                    failed += 1
                    
                processed += 1
                
            except Exception as e:
                logger.exception(f"Unexpected error processing job {job.id}")
                job.mark_error(f"Unexpected error: {str(e)}")
                failed += 1
                processed += 1
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Summary: {processed} processed, {succeeded} succeeded, {failed} failed"
            )
        )

    def _send_to_core(self, job: SyncJob) -> bool:
        """Send job payload to core service."""
        try:
            # Get core service settings
            core_endpoint = getattr(settings, 'CORE_SYNC_ENDPOINT', None)
            core_token = getattr(settings, 'CORE_TOKEN', None)
            
            if not core_endpoint:
                job.mark_error("CORE_SYNC_ENDPOINT not configured")
                return False
                
            if not core_token:
                job.mark_error("CORE_TOKEN not configured")
                return False
            
            # Prepare request
            url = f"{core_endpoint.rstrip('/')}/sync/{job.job_type}/"
            headers = {
                'Authorization': f'Bearer {core_token}',
                'Content-Type': 'application/json'
            }
            
            # Send request with timeout and retries
            response = requests.post(
                url,
                json=job.payload_preview,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully sent job {job.id} to core")
                return True
            else:
                error_msg = f"Core API error: {response.status_code} - {response.text[:500]}"
                job.mark_error(error_msg)
                logger.error(error_msg)
                return False
                
        except requests.exceptions.Timeout:
            error_msg = "Request to core service timed out"
            job.mark_error(error_msg)
            logger.error(error_msg)
            return False
            
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to core service"
            job.mark_error(error_msg)
            logger.error(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            job.mark_error(error_msg)
            logger.exception(error_msg)
            return False
