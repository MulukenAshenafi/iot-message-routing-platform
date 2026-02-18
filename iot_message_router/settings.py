"""
Django settings for iot_message_router project.
"""

from pathlib import Path
import os
import environ
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
# Note: In Docker, environment variables from docker-compose take precedence
# We read .env file but database settings MUST come from os.environ (docker-compose)
env = environ.Env(
    DEBUG=(bool, False)
)
# Read .env file if it exists (for local development)
# CRITICAL: Database settings (DB_NAME, DB_USER, etc.) are read directly from os.environ
# to ensure docker-compose environment variables are never overridden by .env file
# Note: read_env() by default does NOT override existing environment variables
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    # Read .env file (won't override existing environment variables set by docker-compose)
    environ.Env.read_env(env_file)

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY must be set via environment variable - no insecure defaults
SECRET_KEY = env('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY environment variable must be set')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=False)

# ALLOWED_HOSTS must be set via environment variable
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
if not ALLOWED_HOSTS:
    raise ValueError('ALLOWED_HOSTS environment variable must be set and cannot be empty')

# Internal API base URL for server-side HTTP calls (e.g., frontend views using requests)
# In Docker, set this to http://web:8000 to avoid localhost port mapping issues.
INTERNAL_API_BASE_URL = os.environ.get('INTERNAL_API_BASE_URL', '')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # PostGIS support
    
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    
    # Local apps
    'accounts',
    'devices',
    'messages.apps.MessagesConfig',  # Use full path to avoid conflict
    'api',
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'iot_message_router.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'iot_message_router.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
# CRITICAL: Database settings MUST use os.environ directly to ensure docker-compose
# environment variables (DB_NAME=iot_message_router) are never overridden by .env file
# In Docker, docker-compose.yml explicitly sets DB_NAME=iot_message_router which must match POSTGRES_DB

# Get database settings directly from environment (set by docker-compose)
# Do NOT use env() here - it may read from .env file and override docker-compose values
DB_NAME = os.environ.get('DB_NAME', 'iot_message_router')
DB_USER = os.environ.get('DB_USER', 'iot_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'iot_password')
DB_HOST = os.environ.get('DB_HOST', 'db')
DB_PORT = os.environ.get('DB_PORT', '5432')

# Debug: Log database configuration (remove in production if sensitive)
if DEBUG:
    print(f"[DEBUG] Database config: NAME={DB_NAME}, USER={DB_USER}, HOST={DB_HOST}, PORT={DB_PORT}")

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        # Ensure database name is always specified in connection string
        'OPTIONS': {
            'connect_timeout': 10,
        },
        # Prevent connections without database name
        'CONN_MAX_AGE': 0,  # Disable persistent connections to avoid stale connections
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.Owner'

# Authentication URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

# CSRF Settings
# DRF automatically exempts CSRF for API endpoints using token authentication
# Frontend forms need CSRF tokens
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'http://localhost:8000',
    'http://127.0.0.1:8000',
])

# CSRF cookie settings
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)  # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF tokens
CSRF_COOKIE_SAMESITE = 'Lax'

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Settings
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:8000',
    'http://127.0.0.1:8000',
])

CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/0')  # Default to 'redis' for Docker service name
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Fix deprecation warning: explicitly set broker_connection_retry_on_startup
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# API Configuration
API_KEY_LENGTH = env.int('API_KEY_LENGTH', default=32)
MAX_WEBHOOK_RETRIES = env.int('MAX_WEBHOOK_RETRIES', default=3)

# OpenAPI/Swagger Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'IoT Message Routing Platform API',
    'DESCRIPTION': 'REST API for IoT message routing based on group membership, network IDs, and geographic proximity.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# OpenAPI/Swagger Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'IoT Message Routing Platform API',
    'DESCRIPTION': 'REST API for IoT message routing based on group membership, network IDs, and geographic proximity.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
