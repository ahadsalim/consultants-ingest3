from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _

class CustomAdminSite(AdminSite):
    site_header = "سیستم مدیریت اسناد حقوقی"
    site_title = "مدیریت اسناد"
    index_title = "پنل مدیریت"

    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_dict = self._build_app_dict(request, app_label)
        
        # Custom ordering for apps
        app_order = [
            'documents',      # 📄 Documents (سیستم اصلی)
            'masterdata',     # 🗂️ Masterdata  
            'auth',           # 🔐 Authentication and Authorization
            'django_celery_beat',  # ⏰ Periodic Tasks
            'syncbridge',     # 🔄 Syncbridge
            'audit',          # 📊 Audit
            'accounts',       # 👥 Accounts
        ]
        
        # Sort apps according to custom order
        app_list = []
        
        # Add apps in custom order
        for app_name in app_order:
            if app_name in app_dict:
                app_list.append(app_dict[app_name])
        
        # Add any remaining apps not in custom order
        for app_name, app in app_dict.items():
            if app_name not in app_order:
                app_list.append(app)
        
        # Custom app names and icons
        for app in app_list:
            if app['app_label'] == 'documents':
                app['name'] = '📄 اسناد حقوقی'
            elif app['app_label'] == 'masterdata':
                app['name'] = '🗂️ اطلاعات پایه'
            elif app['app_label'] == 'auth':
                app['name'] = '🔐 احراز هویت و مجوزها'
            elif app['app_label'] == 'django_celery_beat':
                app['name'] = '⏰ تسک‌های دوره‌ای'
            elif app['app_label'] == 'syncbridge':
                app['name'] = '🔄 همگام‌سازی'
            elif app['app_label'] == 'audit':
                app['name'] = '📊 حسابرسی'
            elif app['app_label'] == 'accounts':
                app['name'] = '👥 حساب‌های کاربری'
        
        return app_list

# Create custom admin site instance  
admin_site = CustomAdminSite(name='custom_admin')

# Register built-in Django models immediately
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)

# Register django_celery_beat models
try:
    from django_celery_beat.models import (
        PeriodicTask, CrontabSchedule, ClockedSchedule
    )
    from django_celery_beat.admin import (
        PeriodicTaskAdmin, CrontabScheduleAdmin, ClockedScheduleAdmin
    )
    
    admin_site.register(PeriodicTask, PeriodicTaskAdmin)
    admin_site.register(CrontabSchedule, CrontabScheduleAdmin)
    admin_site.register(ClockedSchedule, ClockedScheduleAdmin)
    
    # Register other schedule models with default ModelAdmin
    try:
        from django_celery_beat.models import IntervalSchedule, SolarSchedule
        admin_site.register(IntervalSchedule)
        admin_site.register(SolarSchedule)
    except ImportError:
        pass
        
except ImportError:
    pass
