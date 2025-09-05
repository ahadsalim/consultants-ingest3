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
            'documents',      # 📄 Documents (اسناد حقوقی)
            'basedata',       # 📊 Base Data (اطلاعات پایه) - Virtual app
            'masterdata',     # 🗂️ Masterdata (جداول پایه)
            'auth',           # 🔐 Authentication and Authorization
            'django_celery_beat',  # ⏰ Periodic Tasks
            'syncbridge',     # 🔄 Syncbridge
            'audit',          # 📊 Audit
            'accounts',       # 👥 Accounts
        ]
        
        # Sort apps according to custom order
        app_list = []
        
        for app_name in app_order:
            if app_name in app_dict:
                app_list.append(app_dict[app_name])
            elif app_name == 'basedata':
                # Create virtual app for "اطلاعات پایه" section
                virtual_app = {
                    'name': '📊 اطلاعات پایه',
                    'app_label': 'basedata',
                    'app_url': None,
                    'has_module_perms': True,
                    'models': []
                }
                
                # Move InstrumentWork, InstrumentExpression, InstrumentManifestation models from documents to basedata section
                if 'documents' in app_dict:
                    documents_app = app_dict['documents']
                    basedata_models = []
                    remaining_models = []
                    
                    for model in documents_app.get('models', []):
                        if model.get('object_name') in ['InstrumentWork', 'InstrumentExpression', 'InstrumentManifestation']:
                            basedata_models.append(model)
                        else:
                            remaining_models.append(model)
                    
                    virtual_app['models'] = basedata_models
                    documents_app['models'] = remaining_models
                
                app_list.append(virtual_app)
        
        # Add any remaining apps not in custom order
        for app_name, app in app_dict.items():
            if app_name not in app_order:
                app_list.append(app)
        
        # Custom app names and icons
        for app in app_list:
            if app['app_label'] == 'documents':
                app['name'] = '📄 اسناد حقوقی'
            elif app['app_label'] == 'masterdata':
                app['name'] = '🗂️ جداول پایه'
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
