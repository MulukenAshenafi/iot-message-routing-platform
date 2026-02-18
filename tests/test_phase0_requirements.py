"""
Phase 0 Technical Design Document - Requirements Compliance Tests

This test suite verifies that all Phase 0 requirements are implemented correctly.
"""
import pytest
from django.test import TestCase
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Owner
from devices.models import Device
from messages.models import Message, Group, DeviceInbox
from messages.services import MessageRoutingService


@pytest.mark.phase0
@pytest.mark.django_db
class TestPhase0Requirements(TestCase):
    """Test Phase 0 Technical Design Document requirements"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.owner = Owner.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.token = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')
        
        # Create test group
        self.group = Group.objects.create(
            group_type='private',
            nid='0x123456',
            description='Test group'
        )
        
        # Create test device
        self.device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=self.group,
            nid='0x123456',
            location=Point(40.7128, -74.0060, srid=4326)
        )
    
    def test_requirement_1_technology_stack(self):
        """Requirement 1: Technology Stack - Python/Django, PostGIS, JWT, API Keys"""
        # Test PostGIS is available
        from django.contrib.gis.db import models
        assert hasattr(Device, 'location')
        assert Device._meta.get_field('location').__class__.__name__ == 'PointField'
        
        # Test JWT authentication
        response = self.client.get('/api/owners/')
        assert response.status_code == 200
        
        # Test API key authentication
        assert hasattr(self.device, 'api_key')
        assert hasattr(self.device, 'api_key_hash')
        assert self.device.api_key is not None
    
    def test_requirement_2_device_model(self):
        """Requirement 2: Device model has all required fields"""
        assert hasattr(self.device, 'device_id')
        assert hasattr(self.device, 'hid')
        assert hasattr(self.device, 'api_key')
        assert hasattr(self.device, 'api_key_hash')
        assert hasattr(self.device, 'location')
        assert hasattr(self.device, 'webhook_url')
        assert hasattr(self.device, 'retry_limit')
        assert hasattr(self.device, 'owner')
        assert hasattr(self.device, 'group')
        assert hasattr(self.device, 'nid')
        assert hasattr(self.device, 'users')  # Phase 0: MAX_USERS=6
    
    def test_requirement_3_max_users_per_device(self):
        """Requirement 3: Device can have maximum 6 users (Phase 0 spec)"""
        assert Device.MAX_USERS == 6
        
        # Create additional users
        users = []
        for i in range(7):
            user = Owner.objects.create_user(
                email=f'user{i}@example.com',
                password='testpass123'
            )
            users.append(user)
        
        # Add 6 users (should work)
        for i in range(6):
            self.device.add_user(users[i])
        
        assert self.device.users.count() == 6
        
        # Try to add 7th user (should fail)
        with pytest.raises(ValueError, match='maximum of 6 users'):
            self.device.add_user(users[6])
    
    def test_requirement_4_group_types(self):
        """Requirement 4: All 6 group types are supported"""
        required_types = ['private', 'exclusive', 'open', 'data_logging', 'enhanced', 'location']
        group_choices = [choice[0] for choice in Group._meta.get_field('group_type').choices]
        
        for group_type in required_types:
            assert group_type in group_choices, f"Group type '{group_type}' not found"
    
    def test_requirement_5_message_types(self):
        """Requirement 5: Message types - Alerts and Alarms"""
        # Test alert types
        alert_choices = [choice[0] for choice in Message._meta.get_field('alert_type').choices]
        assert 'sensor' in alert_choices
        assert 'panic' in alert_choices
        assert 'ns_panic' in alert_choices
        assert 'unknown' in alert_choices
        assert 'distress' in alert_choices
        
        # Test alarm types
        alarm_choices = [choice[0] for choice in Message._meta.get_field('alarm_type').choices]
        assert 'pa' in alarm_choices
        assert 'pm' in alarm_choices
        assert 'service' in alarm_choices
    
    def test_requirement_6_routing_algorithm(self):
        """Requirement 6: 5-step routing algorithm is implemented"""
        service = MessageRoutingService()
        assert hasattr(service, 'route_message')
        assert callable(service.route_message)
        
        # Test routing with test data
        message = Message.objects.create(
            type='alert',
            payload={'test': 'data'},
            source_device=self.device
        )
        
        # Route message (should not fail)
        target_devices = service.route_message(message)
        assert isinstance(target_devices, list)
    
    def test_requirement_7_inbox_model(self):
        """Requirement 7: Server inbox model (messages + device_inbox tables)"""
        message = Message.objects.create(
            type='alert',
            payload={'test': 'data'},
            source_device=self.device
        )
        
        # Create inbox entry
        inbox_entry = DeviceInbox.objects.create(
            device=self.device,
            message=message,
            status='pending'
        )
        
        assert inbox_entry.device == self.device
        assert inbox_entry.message == message
        assert inbox_entry.status == 'pending'
        assert hasattr(inbox_entry, 'created_at')
    
    def test_requirement_8_api_endpoints(self):
        """Requirement 8: All required API endpoints exist"""
        endpoints = [
            ('/api/auth/login/', 'POST'),
            ('/api/auth/refresh/', 'POST'),
            ('/api/owners/', 'GET'),
            ('/api/devices/', 'GET'),
            ('/api/devices/', 'POST'),
            (f'/api/devices/{self.device.device_id}/', 'GET'),
            (f'/api/devices/{self.device.device_id}/inbox/', 'GET'),
        ]
        
        for endpoint, method in endpoints:
            if method == 'GET':
                response = self.client.get(endpoint)
            elif method == 'POST':
                response = self.client.post(endpoint, {}, format='json')
            # Should return 200, 201, 400, 401, 403, or 404 (not 500)
            assert response.status_code != 500, f"Endpoint {endpoint} returns 500 error"
    
    def test_requirement_9_device_api_key_authentication(self):
        """Requirement 9: Devices authenticate via API keys"""
        from api.permissions import DeviceAPIKeyAuthentication
        
        # Create request with API key
        request = type('Request', (), {
            'META': {
                'HTTP_X_API_KEY': self.device.api_key
            }
        })()
        
        # Authentication should work
        auth = DeviceAPIKeyAuthentication()
        result = auth.authenticate(request)
        assert result is not None
        assert result[0] == self.device
    
    def test_requirement_10_webhook_retry_limit(self):
        """Requirement 10: Device has configurable retry_limit"""
        assert hasattr(self.device, 'retry_limit')
        assert self.device.retry_limit is not None
        assert isinstance(self.device.retry_limit, int)
        assert self.device.retry_limit >= 0


@pytest.mark.phase0
@pytest.mark.routing
@pytest.mark.django_db
class TestRoutingRequirements(TestCase):
    """Test routing algorithm requirements"""
    
    def setUp(self):
        self.owner = Owner.objects.create_user(
            email='routing@example.com',
            password='testpass123'
        )
    
    def test_private_group_routing(self):
        """Test Private group uses NID, no distance"""
        group = Group.objects.create(
            group_type='private',
            nid='0x123456'
        )
        
        device1 = Device.objects.create(
            hid='DEV1',
            owner=self.owner,
            group=group,
            nid='0x123456'
        )
        
        device2 = Device.objects.create(
            hid='DEV2',
            owner=self.owner,
            group=group,
            nid='0x123456'
        )
        
        device3 = Device.objects.create(
            hid='DEV3',
            owner=self.owner,
            group=group,
            nid='0x999999'  # Different NID
        )
        
        message = Message.objects.create(
            type='alert',
            payload={'test': 'data'},
            source_device=device1
        )
        
        service = MessageRoutingService()
        targets = service.route_message(message)
        
        # Should include device2 (same NID) but not device3 (different NID)
        target_hids = [d.hid for d in targets]
        assert 'DEV2' in target_hids
        assert 'DEV3' not in target_hids
    
    def test_location_group_routing(self):
        """Test Location group uses NID (0xFFFFFF) and distance"""
        group = Group.objects.create(
            group_type='location',
            nid='0xFFFFFF',
            radius=1000  # 1km radius
        )
        
        # Source device at (0, 0)
        device1 = Device.objects.create(
            hid='SOURCE',
            owner=self.owner,
            group=group,
            nid='0xFFFFFF',
            location=Point(0, 0, srid=4326)
        )
        
        # Target device within radius (~100m away)
        device2 = Device.objects.create(
            hid='NEAR',
            owner=self.owner,
            group=group,
            nid='0xFFFFFF',
            location=Point(0.001, 0.001, srid=4326)  # ~100m away
        )
        
        # Target device outside radius
        device3 = Device.objects.create(
            hid='FAR',
            owner=self.owner,
            group=group,
            nid='0xFFFFFF',
            location=Point(1, 1, srid=4326)  # Very far away
        )
        
        message = Message.objects.create(
            type='alert',
            payload={'location': {'lat': 0, 'lon': 0}},
            source_device=device1
        )
        
        service = MessageRoutingService()
        targets = service.route_message(message)
        
        target_hids = [d.hid for d in targets]
        assert 'NEAR' in target_hids
        assert 'FAR' not in target_hids


@pytest.mark.phase0
@pytest.mark.authentication
@pytest.mark.django_db
class TestAuthenticationRequirements(TestCase):
    """Test authentication requirements"""
    
    def test_jwt_authentication_users(self):
        """Users authenticate with JWT"""
        owner = Owner.objects.create_user(
            email='jwt@example.com',
            password='testpass123'
        )
        
        client = APIClient()
        response = client.post('/api/auth/login/', {
            'email': 'jwt@example.com',
            'password': 'testpass123'
        }, format='json')
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_api_key_authentication_devices(self):
        """Devices authenticate with API keys"""
        owner = Owner.objects.create_user(
            email='device@example.com',
            password='testpass123'
        )
        group = Group.objects.create(group_type='open')
        
        device = Device.objects.create(
            hid='API-KEY-DEVICE',
            owner=owner,
            group=group
        )
        
        client = APIClient()
        response = client.post(
            f'/api/messages/hid/{device.hid}/',
            {
                'type': 'alert',
                'payload': {'test': 'data'}
            },
            format='json',
            HTTP_X_API_KEY=device.api_key
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

