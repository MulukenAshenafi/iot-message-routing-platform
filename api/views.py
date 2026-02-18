"""
API utility views including health checks
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from celery import current_app
import os

# Redis import with graceful fallback
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@require_http_methods(["GET"])
@csrf_exempt
def health_check(request):
    """
    Health check endpoint for monitoring and load balancers
    GET /api/health/
    
    Returns:
    - 200 OK: All systems operational
    - 503 Service Unavailable: One or more systems unhealthy
    """
    status = {
        'status': 'healthy',
        'version': '1.0.0',
        'checks': {}
    }
    
    overall_healthy = True
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = 'healthy'
            db_error = None
    except Exception as e:
        db_status = 'unhealthy'
        db_error = str(e)
        overall_healthy = False
    
    status['checks']['database'] = {
        'status': db_status,
        'error': db_error
    }
    
    # Redis check
    if not REDIS_AVAILABLE:
        redis_status = 'unavailable'
        redis_error = 'redis Python package not installed'
        overall_healthy = False
    else:
        try:
            redis_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
            # Parse Redis URL
            if redis_url.startswith('redis://'):
                redis_url = redis_url.replace('redis://', '')
                if '/' in redis_url:
                    host_port, db = redis_url.split('/')
                else:
                    host_port, db = redis_url, '0'
                if ':' in host_port:
                    host, port = host_port.split(':')
                else:
                    host, port = host_port, '6379'
                
                r = redis.Redis(host=host, port=int(port), db=int(db), socket_connect_timeout=2)
                r.ping()
                redis_status = 'healthy'
                redis_error = None
            else:
                redis_status = 'unhealthy'
                redis_error = 'Invalid Redis URL format'
                overall_healthy = False
        except Exception as e:
            redis_status = 'unhealthy'
            redis_error = str(e)
            overall_healthy = False
    
    status['checks']['redis'] = {
        'status': redis_status,
        'error': redis_error
    }
    
    # Celery worker check
    try:
        inspect = current_app.control.inspect()
        active_workers = inspect.active()
        if active_workers:
            celery_status = 'healthy'
            celery_workers = list(active_workers.keys())
            celery_error = None
        else:
            celery_status = 'degraded'
            celery_workers = []
            celery_error = 'No active Celery workers found'
            # Don't fail overall health if Celery is degraded (webhooks may not be critical)
    except Exception as e:
        celery_status = 'unhealthy'
        celery_workers = []
        celery_error = str(e)
        # Celery failure doesn't necessarily mean API is down
        # Only mark as unhealthy if critical
    
    status['checks']['celery'] = {
        'status': celery_status,
        'workers': celery_workers,
        'error': celery_error
    }
    
    # Update overall status
    if not overall_healthy:
        status['status'] = 'unhealthy'
    
    # Return appropriate HTTP status
    http_status = 200 if overall_healthy else 503
    
    return JsonResponse(status, status=http_status)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_info(request):
    """
    API information endpoint
    GET /api/v1/info/
    """
    return Response({
        'name': 'IoT Message Routing Platform API',
        'version': '1.0.0',
        'description': 'REST API for IoT message routing based on group membership, network IDs, and geographic proximity',
        'documentation': {
            'swagger': '/api/docs/',
            'schema': '/api/schema/',
        },
        'endpoints': {
            'health': '/api/health/',
            'authentication': {
                'register': '/api/v1/auth/register/',
                'login': '/api/v1/auth/login/',
                'refresh': '/api/v1/auth/refresh/',
                'logout': '/api/v1/auth/logout/',
            },
            'resources': {
                'owners': '/api/v1/owners/',
                'devices': '/api/v1/devices/',
                'messages': '/api/v1/messages/',
                'groups': '/api/v1/groups/',
            },
        }
    })
