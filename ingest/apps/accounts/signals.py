from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import LoginEvent


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login events for security auditing."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    LoginEvent.objects.create(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )


def get_client_ip(request):
    """Get the client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
