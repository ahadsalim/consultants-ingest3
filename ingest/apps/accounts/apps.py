from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ingest.apps.accounts'
    verbose_name = 'حساب‌های کاربری'

    def ready(self):
        import ingest.apps.accounts.signals
