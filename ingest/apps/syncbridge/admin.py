from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import SyncJob, SyncJobStatus
from ingest.admin import admin_site


class SyncJobAdmin(SimpleHistoryAdmin):
    list_display = ('job_type', 'target_id', 'status_badge', 'retry_count', 'created_at', 'completed_at')
    list_filter = ('status', 'job_type', 'created_at')
    search_fields = ('target_id', 'last_error')
    readonly_fields = ('id', 'created_at', 'updated_at', 'completed_at')
    
    actions = ['retry_failed_jobs', 'reset_jobs']

    def status_badge(self, obj):
        colors = {
            SyncJobStatus.PENDING: 'orange',
            SyncJobStatus.RUNNING: 'blue',
            SyncJobStatus.SUCCESS: 'green',
            SyncJobStatus.ERROR: 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = 'وضعیت'

    def retry_failed_jobs(self, request, queryset):
        count = 0
        for job in queryset:
            if job.can_retry:
                job.status = SyncJobStatus.PENDING
                job.last_error = ''
                job.next_retry_at = None
                job.save()
                count += 1
        self.message_user(request, f'{count} کار برای تلاش مجدد تنظیم شد.')
    retry_failed_jobs.short_description = 'تلاش مجدد کارهای ناموفق'

    def reset_jobs(self, request, queryset):
        count = 0
        for job in queryset:
            job.status = SyncJobStatus.PENDING
            job.retry_count = 0
            job.last_error = ''
            job.next_retry_at = None
            job.completed_at = None
            job.save()
            count += 1
        self.message_user(request, f'{count} کار بازنشانی شد.')
    reset_jobs.short_description = 'بازنشانی کارها'


# Register models with custom admin site
admin_site.register(SyncJob, SyncJobAdmin)
