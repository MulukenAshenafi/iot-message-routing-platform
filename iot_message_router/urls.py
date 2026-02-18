"""
URL configuration for iot_message_router project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from accounts.views import OwnerViewSet, register_user, logout_user
from devices.views import DeviceViewSet
from messages.views import MessageViewSet, GroupViewSet, network_devices_by_hid, network_owners_by_owner_id
from api.views import health_check, api_info


@require_http_methods(["GET"])
def root_view(request):
    """Root endpoint with API information"""
    return JsonResponse({
        'message': 'IoT Message Routing API',
        'version': '1.0.0',
        'endpoints': {
            'api_root': '/api/',
            'admin_dashboard': '/admin/',  # Custom admin dashboard
            'django_admin': '/django-admin/',  # Django's built-in admin (if needed)
            'authentication': {
                'register': '/api/auth/register/',
                'login': '/api/auth/login/',
                'refresh': '/api/auth/refresh/',
                'logout': '/api/auth/logout/',
            },
            'resources': {
                'owners': '/api/owners/',
                'devices': '/api/devices/',
                'messages': '/api/messages/',
                'groups': '/api/groups/',
            },
            'network': {
                'devices_by_hid': '/api/network/hid/{hid}/',
                'owners_by_id': '/api/network/owners/{owner_id}/',
            }
        },
        'documentation': 'Access /api/ for browsable API documentation'
    })


# Create router and register viewsets for v1 API
router_v1 = DefaultRouter()
router_v1.register(r'owners', OwnerViewSet, basename='owner')
router_v1.register(r'devices', DeviceViewSet, basename='device')
router_v1.register(r'messages', MessageViewSet, basename='message')
router_v1.register(r'groups', GroupViewSet, basename='group')

# Legacy router (backward compatibility)
router_legacy = DefaultRouter()
router_legacy.register(r'owners', OwnerViewSet, basename='owner-legacy')
router_legacy.register(r'devices', DeviceViewSet, basename='device-legacy')
router_legacy.register(r'messages', MessageViewSet, basename='message-legacy')
router_legacy.register(r'groups', GroupViewSet, basename='group-legacy')

urlpatterns = [
    # Frontend routes (must come before Django admin to catch /admin/ for custom admin dashboard)
    path('', include('frontend.urls')),
    
    # Django built-in admin (moved to /django-admin/ - custom admin dashboard is at /admin/)
    path('django-admin/', admin.site.urls),  # Django's built-in admin at /django-admin/
    
    # Health check (no versioning, always available)
    path('api/health/', health_check, name='health_check'),
    
    # API v1 routes
    path('api/v1/', include(router_v1.urls)),
    path('api/v1/info/', api_info, name='api_info'),
    
    # API v1 Authentication
    path('api/v1/auth/register/', register_user, name='register_v1'),
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair_v1'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh_v1'),
    path('api/v1/auth/logout/', logout_user, name='logout_v1'),
    
    # API v1 Network queries
    path('api/v1/network/hid/<str:hid>/', network_devices_by_hid, name='network_devices_by_hid_v1'),
    path('api/v1/network/owners/<int:owner_id>/', network_owners_by_owner_id, name='network_owners_by_owner_id_v1'),
    
    # Legacy API routes (backward compatibility - redirect to v1)
    path('api/', include(router_legacy.urls)),
    path('api/auth/register/', register_user, name='register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', logout_user, name='logout'),
    path('api/network/hid/<str:hid>/', network_devices_by_hid, name='network_devices_by_hid'),
    path('api/network/owners/<int:owner_id>/', network_owners_by_owner_id, name='network_owners_by_owner_id'),
    
    # OpenAPI Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
