from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import LoginEvent
from ingest.admin import admin_site


class LoginEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'timestamp', 'success')
    list_filter = ('success', 'timestamp')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('id', 'user', 'ip_address', 'user_agent', 'timestamp', 'success')
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Register models with custom admin site
admin_site.register(LoginEvent, LoginEventAdmin)
