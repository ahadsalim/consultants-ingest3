"""Production settings for ingest project."""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Security settings
FORCE_INSECURE_HTTP = os.getenv('FORCE_INSECURE_HTTP', 'false').lower() == 'true'
SECURE_SSL_REDIRECT = False if FORCE_INSECURE_HTTP else True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database connection pooling for production
DATABASES['default'].update({
    'CONN_MAX_AGE': 60,
})

# Static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Force Django to serve static files in production
STATIC_URL = '/static/'
STATIC_ROOT = '/app/staticfiles'

# Whitenoise for static files serving
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

# MinIO settings for production
AWS_ACCESS_KEY_ID = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
AWS_STORAGE_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'advisor-docs')
AWS_S3_ENDPOINT_URL = os.getenv('MINIO_ENDPOINT', 'http://core-minio:9000')
AWS_S3_USE_SSL = os.getenv('MINIO_USE_SSL', 'False').lower() == 'true'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Use MinIO for file storage by default
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Public URL for MinIO files (used for generating download links)
MINIO_STORAGE_MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"

# Logging for production (console only for Docker)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'ingest': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
