"""
Custom permissions for API authentication
"""
from rest_framework import permissions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from devices.models import Device
import hashlib


class DeviceAPIKeyAuthentication(BaseAuthentication):
    """
    Custom authentication for devices using API keys
    Devices authenticate via X-API-Key header
    """
    
    def authenticate(self, request):
        # Check for X-API-Key header (case-insensitive)
        api_key = None
        for header_name in ['HTTP_X_API_KEY', 'X_API_KEY', 'HTTP_X-API-KEY']:
            api_key = request.META.get(header_name)
            if api_key:
                break
        
        # Also check in headers dict (for some frameworks)
        if not api_key and hasattr(request, 'headers'):
            api_key = request.headers.get('X-API-Key') or request.headers.get('x-api-key')
        
        if not api_key:
            return None
        
        try:
            # Hash the provided API key
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Find device by API key hash
            device = Device.objects.get(api_key_hash=api_key_hash, active=True)
            return (device, None)  # Return (user, auth) tuple
        except Device.DoesNotExist:
            # Don't raise here, just return None to allow other auth methods
            return None
        except Exception:
            return None


class IsDeviceOwner(permissions.BasePermission):
    """
    Permission to check if user owns the device
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is the owner of the device
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False


class IsDeviceOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read access to all, but write only to device owners
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False

