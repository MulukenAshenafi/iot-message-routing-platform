"""
Pytest configuration and shared fixtures
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from accounts.models import Owner
from devices.models import Device
from messages.models import Group, Message, DeviceInbox

Owner = get_user_model()


@pytest.fixture
def api_client():
    """DRF API client"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return Owner.objects.create_user(
        email='admin@test.com',
        username='admin',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
        first_name='Admin',
        last_name='User'
    )


@pytest.fixture
def regular_user(db):
    """Create regular user"""
    return Owner.objects.create_user(
        email='user@test.com',
        username='testuser',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def authenticated_client(api_client, regular_user):
    """Authenticated API client"""
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Admin authenticated API client"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def groups(db):
    """Create all group types"""
    group_types = [
        ('private', 'Private Group', 'test-nid-001', None),
        ('exclusive', 'Exclusive Group', 'test-nid-002', None),
        ('open', 'Open Group', None, 10.0),
        ('data_logging', 'Data Logging Group', 'test-nid-003', None),
        ('enhanced', 'Enhanced Group', 'test-nid-004', 5.0),
        ('location', 'Location Group', '0xFFFFFF', 15.0),
    ]
    
    created_groups = []
    for group_type, description, nid, radius in group_types:
        group = Group.objects.create(
            group_type=group_type,
            description=description,
            nid=nid,
            radius=radius
        )
        created_groups.append(group)
    
    return created_groups


@pytest.fixture
def device(regular_user, groups):
    """Create test device"""
    device = Device.objects.create(
        hid='TEST-DEVICE-001',
        owner=regular_user,
        group=groups[0],  # Private group
        nid='test-nid-001',
        location=Point(-79.3832, 43.6532, srid=4326),  # Toronto
        webhook_url='http://example.com/webhook',
        retry_limit=3
    )
    return device


@pytest.fixture
def devices(regular_user, groups):
    """Create multiple test devices"""
    locations = [
        (-79.3832, 43.6532),  # Toronto
        (-79.3833, 43.6533),  # 100m away
        (-79.4000, 43.6600),  # 1.5km away
    ]
    
    devices = []
    for i, (lon, lat) in enumerate(locations):
        device = Device.objects.create(
            hid=f'TEST-DEVICE-{i+1:03d}',
            owner=regular_user,
            group=groups[4],  # Enhanced group (uses distance)
            nid='test-nid-004',
            location=Point(lon, lat, srid=4326),
            retry_limit=3
        )
        devices.append(device)
    
    return devices


@pytest.fixture
def message(device):
    """Create test message"""
    return Message.objects.create(
        source_device=device,
        type='alert',
        alert_type='sensor',
        payload={'temperature': 25.5, 'humidity': 60}
    )


@pytest.fixture
def device_inbox(device, message):
    """Create device inbox entry"""
    return DeviceInbox.objects.create(
        device=device,
        message=message,
        status='pending'
    )

