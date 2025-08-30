from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ingest.apps.audit'
    verbose_name = 'حسابرسی'
