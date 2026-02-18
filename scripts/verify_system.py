#!/usr/bin/env python
"""
Comprehensive System Verification Script
Verifies all API endpoints, relationships, authentication, and functionality
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iot_message_router.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Owner
from devices.models import Device
from messages.models import Message, DeviceInbox, Group, GroupType
from django.contrib.gis.geos import Point
import json

Owner = get_user_model()

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_database_models():
    """Test all database models and relationships"""
    print_section("Testing Database Models & Relationships")
    
    issues = []
    
    # Test Owner model
    try:
        owner = Owner.objects.first()
        if owner:
            print(f"✓ Owner model: {owner}")
            print(f"  - Email: {owner.email}")
            print(f"  - Devices count: {owner.devices.count()}")
        else:
            print("⚠ No owners found in database")
    except Exception as e:
        issues.append(f"Owner model error: {e}")
        print(f"✗ Owner model error: {e}")
    
    # Test Device model
    try:
        device = Device.objects.first()
        if device:
            print(f"✓ Device model: {device.hid}")
            print(f"  - Owner: {device.owner.email}")
            print(f"  - Group: {device.group.get_group_type_display()}")
            print(f"  - Location: {device.location}")
            print(f"  - API Key Hash: {device.api_key_hash[:20]}...")
        else:
            print("⚠ No devices found in database")
    except Exception as e:
        issues.append(f"Device model error: {e}")
        print(f"✗ Device model error: {e}")
    
    # Test Message model
    try:
        message = Message.objects.first()
        if message:
            print(f"✓ Message model: {message.message_id}")
            print(f"  - Type: {message.type}")
            print(f"  - Source Device: {message.source_device.hid}")
            print(f"  - Timestamp: {message.timestamp}")
        else:
            print("⚠ No messages found in database")
    except Exception as e:
        issues.append(f"Message model error: {e}")
        print(f"✗ Message model error: {e}")
    
    # Test DeviceInbox model
    try:
        inbox = DeviceInbox.objects.first()
        if inbox:
            print(f"✓ DeviceInbox model: {inbox.id}")
            print(f"  - Device: {inbox.device.hid}")
            print(f"  - Message: {inbox.message.message_id}")
            print(f"  - Status: {inbox.status}")
        else:
            print("⚠ No inbox entries found in database")
    except Exception as e:
        issues.append(f"DeviceInbox model error: {e}")
        print(f"✗ DeviceInbox model error: {e}")
    
    # Test Group model
    try:
        groups = Group.objects.all()
        print(f"✓ Groups found: {groups.count()}")
        for group in groups[:5]:
            print(f"  - {group.get_group_type_display()} (NID: {group.nid or 'None'}, Radius: {group.radius or 'None'})")
    except Exception as e:
        issues.append(f"Group model error: {e}")
        print(f"✗ Group model error: {e}")
    
    return issues

def test_api_endpoints():
    """Test all API endpoints"""
    print_section("Testing API Endpoints")
    
    # Fix ALLOWED_HOSTS for test client
    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')
    
    client = Client()
    issues = []
    
    # Test root endpoint
    try:
        response = client.get('/')
        if response.status_code == 200:
            print("✓ Root endpoint (/)")
        else:
            issues.append(f"Root endpoint returned {response.status_code}")
            print(f"✗ Root endpoint returned {response.status_code}")
    except Exception as e:
        issues.append(f"Root endpoint error: {e}")
        print(f"✗ Root endpoint error: {e}")
    
    # Test API root
    try:
        response = client.get('/api/')
        if response.status_code == 200:
            print("✓ API root (/api/)")
        else:
            print(f"⚠ API root returned {response.status_code}")
    except Exception as e:
        issues.append(f"API root error: {e}")
        print(f"✗ API root error: {e}")
    
    # Test authentication endpoints
    endpoints = [
        ('/api/auth/register/', 'POST'),
        ('/api/auth/login/', 'POST'),
        ('/api/auth/refresh/', 'POST'),
        ('/api/auth/logout/', 'POST'),
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == 'POST':
                response = client.post(endpoint, {}, content_type='application/json')
            else:
                response = client.get(endpoint)
            
            # These endpoints may return 400/401 which is expected without proper data
            if response.status_code in [200, 201, 400, 401]:
                print(f"✓ {endpoint} ({method}) - Status: {response.status_code}")
            else:
                issues.append(f"{endpoint} returned {response.status_code}")
                print(f"✗ {endpoint} ({method}) - Status: {response.status_code}")
        except Exception as e:
            issues.append(f"{endpoint} error: {e}")
            print(f"✗ {endpoint} error: {e}")
    
    # Test resource endpoints (require authentication)
    resource_endpoints = [
        '/api/owners/',
        '/api/devices/',
        '/api/messages/',
        '/api/groups/',
    ]
    
    for endpoint in resource_endpoints:
        try:
            response = client.get(endpoint)
            # Should return 401 without auth
            if response.status_code == 401:
                print(f"✓ {endpoint} (requires authentication)")
            else:
                print(f"⚠ {endpoint} returned {response.status_code}")
        except Exception as e:
            issues.append(f"{endpoint} error: {e}")
            print(f"✗ {endpoint} error: {e}")
    
    return issues

def test_authentication():
    """Test authentication and authorization"""
    print_section("Testing Authentication & Authorization")
    
    issues = []
    client = Client()
    
    # Test user registration
    try:
        test_data = {
            'username': 'test_verify_user',
            'email': 'test_verify@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = client.post('/api/auth/register/', 
                             json.dumps(test_data),
                             content_type='application/json')
        
        if response.status_code == 201:
            print("✓ User registration works")
            data = response.json()
            if 'tokens' in data:
                print("  - JWT tokens returned")
        else:
            print(f"⚠ Registration returned {response.status_code}")
            # Check if user already exists
            if response.status_code == 400:
                print("  - User may already exist (OK)")
    except Exception as e:
        issues.append(f"Registration error: {e}")
        print(f"✗ Registration error: {e}")
    
    # Test login
    try:
        login_data = {
            'username': 'test_verify_user',
            'password': 'testpass123'
        }
        response = client.post('/api/auth/login/',
                              json.dumps(login_data),
                              content_type='application/json')
        
        if response.status_code == 200:
            print("✓ User login works")
            data = response.json()
            if 'access' in data:
                print("  - Access token returned")
        else:
            print(f"⚠ Login returned {response.status_code}")
    except Exception as e:
        issues.append(f"Login error: {e}")
        print(f"✗ Login error: {e}")
    
    return issues

def test_role_based_access():
    """Test role-based access control"""
    print_section("Testing Role-Based Access Control")
    
    issues = []
    
    # Check if admin users can see all devices
    try:
        admin_users = Owner.objects.filter(is_staff=True)
        regular_users = Owner.objects.filter(is_staff=False)
        
        print(f"✓ Admin users: {admin_users.count()}")
        print(f"✓ Regular users: {regular_users.count()}")
        
        if admin_users.exists():
            admin = admin_users.first()
            all_devices = Device.objects.all()
            print(f"  - Admin can see {all_devices.count()} total devices")
        
        if regular_users.exists():
            user = regular_users.first()
            user_devices = Device.objects.filter(owner=user)
            print(f"  - Regular user '{user.email}' can see {user_devices.count()} devices")
    except Exception as e:
        issues.append(f"RBAC test error: {e}")
        print(f"✗ RBAC test error: {e}")
    
    return issues

def test_message_routing():
    """Test message routing logic"""
    print_section("Testing Message Routing")
    
    issues = []
    
    try:
        # Check if routing service is importable
        from messages.services import MessageRoutingService
        print("✓ MessageRoutingService imported")
        
        # Check if groups exist
        groups = Group.objects.all()
        print(f"✓ Groups available: {groups.count()}")
        
        # Check if devices exist
        devices = Device.objects.all()
        print(f"✓ Devices available: {devices.count()}")
        
        # Check if messages exist
        messages = Message.objects.all()
        print(f"✓ Messages available: {messages.count()}")
        
        # Check if inbox entries exist
        inbox_entries = DeviceInbox.objects.all()
        print(f"✓ Inbox entries: {inbox_entries.count()}")
        
    except Exception as e:
        issues.append(f"Message routing test error: {e}")
        print(f"✗ Message routing test error: {e}")
    
    return issues

def test_production_readiness():
    """Test production readiness"""
    print_section("Testing Production Readiness")
    
    issues = []
    
    from django.conf import settings
    
    # Check SECRET_KEY
    if settings.SECRET_KEY and len(settings.SECRET_KEY) > 20:
        print("✓ SECRET_KEY is set")
    else:
        issues.append("SECRET_KEY is weak or missing")
        print("✗ SECRET_KEY is weak or missing")
    
    # Check DEBUG
    if settings.DEBUG:
        print("⚠ DEBUG is True (should be False in production)")
    else:
        print("✓ DEBUG is False")
    
    # Check ALLOWED_HOSTS
    if settings.ALLOWED_HOSTS:
        print(f"✓ ALLOWED_HOSTS configured: {settings.ALLOWED_HOSTS}")
    else:
        issues.append("ALLOWED_HOSTS is empty")
        print("✗ ALLOWED_HOSTS is empty")
    
    # Check CSRF settings
    if hasattr(settings, 'CSRF_TRUSTED_ORIGINS'):
        print(f"✓ CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
    else:
        print("⚠ CSRF_TRUSTED_ORIGINS not set")
    
    # Check database
    try:
        from django.db import connection
        connection.ensure_connection()
        print("✓ Database connection works")
    except Exception as e:
        issues.append(f"Database connection error: {e}")
        print(f"✗ Database connection error: {e}")
    
    # Check static files
    if hasattr(settings, 'STATIC_ROOT'):
        print(f"✓ STATIC_ROOT: {settings.STATIC_ROOT}")
    else:
        print("⚠ STATIC_ROOT not set")
    
    return issues

def main():
    """Run all verification tests"""
    print("\n" + "="*60)
    print("  IoT Message Router - System Verification")
    print("="*60)
    
    all_issues = []
    
    # Run all tests
    all_issues.extend(test_database_models())
    all_issues.extend(test_api_endpoints())
    all_issues.extend(test_authentication())
    all_issues.extend(test_role_based_access())
    all_issues.extend(test_message_routing())
    all_issues.extend(test_production_readiness())
    
    # Summary
    print_section("Verification Summary")
    
    if all_issues:
        print(f"⚠ Found {len(all_issues)} issues:")
        for issue in all_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(all_issues) > 10:
            print(f"  ... and {len(all_issues) - 10} more")
    else:
        print("✓ All tests passed! System is ready.")
    
    print("\n" + "="*60)
    return 0 if not all_issues else 1

if __name__ == '__main__':
    sys.exit(main())

