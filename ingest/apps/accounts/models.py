import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class LoginEvent(models.Model):
    """Track user login events for security auditing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='login_events')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'رویداد ورود'
        verbose_name_plural = 'رویدادهای ورود'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"
