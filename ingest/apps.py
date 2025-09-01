from django.apps import AppConfig


class IngestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ingest'

    def ready(self):
        """Register built-in Django models with custom admin site after apps are loaded"""
        print("DEBUG: IngestConfig.ready() called")
        from django.contrib.auth.models import User, Group
        from django.contrib.auth.admin import UserAdmin, GroupAdmin
        from .admin import admin_site
        
        # Register User and Group models with custom admin site
        admin_site.register(User, UserAdmin)
        admin_site.register(Group, GroupAdmin)
        print(f"DEBUG: Registered User and Group. Total models: {len(admin_site._registry)}")
        
        # Register django_celery_beat models
        try:
            from django_celery_beat.models import (
                PeriodicTask, CrontabSchedule, IntervalSchedule, 
                SolarSchedule, ClockedSchedule
            )
            from django_celery_beat.admin import (
                PeriodicTaskAdmin, CrontabScheduleAdmin, IntervalScheduleAdmin,
                SolarScheduleAdmin, ClockedScheduleAdmin
            )
            
            admin_site.register(PeriodicTask, PeriodicTaskAdmin)
            admin_site.register(CrontabSchedule, CrontabScheduleAdmin)
            admin_site.register(IntervalSchedule, IntervalScheduleAdmin)
            admin_site.register(SolarSchedule, SolarScheduleAdmin)
            admin_site.register(ClockedSchedule, ClockedScheduleAdmin)
            print(f"DEBUG: Registered celery beat models. Total models: {len(admin_site._registry)}")
        except ImportError as e:
            print(f"DEBUG: Could not import celery beat models: {e}")
