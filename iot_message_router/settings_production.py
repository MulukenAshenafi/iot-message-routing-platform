"""
Production settings for iot_message_router project.
Import this in production by setting DJANGO_SETTINGS_MODULE
"""
from .settings import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Security settings for production
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Allowed hosts - set in environment (required)
ALLOWED_HOSTS_STR = os.environ.get('ALLOWED_HOSTS', '')
if not ALLOWED_HOSTS_STR:
    raise ValueError('ALLOWED_HOSTS environment variable must be set in production')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_STR.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError('ALLOWED_HOSTS cannot be empty in production')

# Secret key from environment (required)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY environment variable must be set in production')
if SECRET_KEY.startswith('django-insecure-'):
    raise ValueError('SECRET_KEY cannot use insecure default in production')

# Ensure DEBUG is False in production
if DEBUG:
    raise ValueError('DEBUG must be False in production environment')

# Database - use environment variables
DATABASES['default'].update({
    'NAME': os.environ.get('DB_NAME', DATABASES['default']['NAME']),
    'USER': os.environ.get('DB_USER', DATABASES['default']['USER']),
    'PASSWORD': os.environ.get('DB_PASSWORD', DATABASES['default']['PASSWORD']),
    'HOST': os.environ.get('DB_HOST', DATABASES['default']['HOST']),
    'PORT': os.environ.get('DB_PORT', DATABASES['default']['PORT']),
})

# Logging
# Ensure logs directory exists
logs_dir = os.path.join(BASE_DIR, 'logs')
os.makedirs(logs_dir, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(logs_dir, 'django.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'iot_message_router': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Sentry error tracking (optional - set SENTRY_DSN environment variable)
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
            ],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=os.environ.get('ENVIRONMENT', 'production'),
        )
    except ImportError:
        # Sentry SDK not installed, skip
        pass

# Static files - use CDN or proper static file server in production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

