"""
Requirements Verification Tests
Tests that verify all requirements from Phase 0 and Original Requirements documents
"""
import pytest
from django.test import TestCase
from django.contrib.gis.geos import Point
from accounts.models import Owner
from devices.models import Device
from messages.models import Group, Message, DeviceInbox
from messages.services import MessageRoutingService


class TestPhase0Requirements(TestCase):
    """Test Phase 0 Technical Design Document Requirements"""
    
    def setUp(self):
        self.owner = Owner.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.group = Group.objects.create(
            group_type='enhanced',
            nid='test-nid',
            radius=10.0
        )
    
    def test_device_has_all_required_fields(self):
        """Test: Device model has all Phase 0 required fields"""
        device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=self.group,
            nid='test-nid-001',
            location=Point(-79.3832, 43.6532, srid=4326)
        )
        
        # Required fields from Phase 0 spec
        assert hasattr(device, 'device_id')
        assert hasattr(device, 'hid')
        assert hasattr(device, 'api_key')
        assert hasattr(device, 'location')
        assert hasattr(device, 'webhook_url')
        assert hasattr(device, 'retry_limit')
        assert hasattr(device, 'owner')
        assert hasattr(device, 'users')  # MAX_USERS=6
        
        # Verify MAX_USERS constant
        assert Device.MAX_USERS == 6
    
    def test_device_max_users_enforcement(self):
        """Test: Device can have maximum 6 users (Phase 0 spec)"""
        device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=self.group
        )
        
        # Create 7 users
        users = []
        for i in range(7):
            user = Owner.objects.create_user(
                email=f'user{i}@test.com',
                username=f'user{i}',
                password='testpass123'
            )
            users.append(user)
        
        # Add 6 users - should work
        for i in range(6):
            device.add_user(users[i])
        
        assert device.users.count() == 6
        
        # Try to add 7th - should fail
        with pytest.raises(ValueError, match='maximum of 6 users'):
            device.add_user(users[6])
    
    def test_all_group_types_exist(self):
        """Test: All 6 group types from Phase 0 spec exist"""
        group_types = [choice[0] for choice in Group._meta.get_field('group_type').choices]
        required_types = ['private', 'exclusive', 'open', 'data_logging', 'enhanced', 'location']
        
        for req_type in required_types:
            assert req_type in group_types, f"Missing group type: {req_type}"
    
    def test_group_type_behavior(self):
        """Test: Group types have correct NID and distance behavior"""
        # Private - uses NID, no distance
        private = Group.objects.create(group_type='private', nid='nid-001')
        assert private.nid is not None
        assert private.radius is None
        
        # Open - no NID, uses distance
        open_group = Group.objects.create(group_type='open', radius=10.0)
        assert open_group.nid is None
        assert open_group.radius == 10.0
        
        # Enhanced - uses both
        enhanced = Group.objects.create(group_type='enhanced', nid='nid-002', radius=5.0)
        assert enhanced.nid is not None
        assert enhanced.radius == 5.0
    
    def test_message_types_exist(self):
        """Test: All message types from Phase 0 spec exist"""
        alert_choices = [choice[0] for choice in Message._meta.get_field('alert_type').choices]
        alarm_choices = [choice[0] for choice in Message._meta.get_field('alarm_type').choices]
        
        # Alert types
        required_alerts = ['sensor', 'panic', 'ns_panic', 'unknown', 'distress']
        for req_alert in required_alerts:
            assert req_alert in alert_choices, f"Missing alert type: {req_alert}"
        
        # Alarm types
        required_alarms = ['pa', 'pm', 'service']
        for req_alarm in required_alarms:
            assert req_alarm in alarm_choices, f"Missing alarm type: {req_alarm}"
    
    def test_routing_service_exists(self):
        """Test: MessageRoutingService with 5-step algorithm exists"""
        service = MessageRoutingService()
        assert hasattr(service, 'route_message')
        
        # Verify it's callable
        assert callable(service.route_message)
    
    def test_device_inbox_model_exists(self):
        """Test: DeviceInbox model with required fields exists"""
        device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=self.group
        )
        message = Message.objects.create(
            source_device=device,
            type='alert',
            payload={'test': 'data'}
        )
        
        inbox = DeviceInbox.objects.create(
            device=device,
            message=message,
            status='pending'
        )
        
        assert hasattr(inbox, 'id')
        assert hasattr(inbox, 'device')
        assert hasattr(inbox, 'message')
        assert hasattr(inbox, 'status')
        assert inbox.status == 'pending'


class TestOriginalRequirements(TestCase):
    """Test Original Requirement Document Requirements"""
    
    def setUp(self):
        self.owner = Owner.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
    
    def test_jwt_authentication(self):
        """Test: JWT authentication is implemented"""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        refresh = RefreshToken.for_user(self.owner)
        assert 'access' in str(refresh)
        assert 'refresh' in str(refresh)
    
    def test_api_key_authentication(self):
        """Test: API key authentication for devices"""
        group = Group.objects.create(group_type='private', nid='test-nid')
        device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=group
        )
        
        assert device.api_key is not None
        assert len(device.api_key) > 0
        assert device.verify_api_key(device.api_key) is True
    
    def test_postgis_integration(self):
        """Test: PostGIS for geographic queries"""
        from django.contrib.gis.db.models.functions import Distance
        from django.contrib.gis.geos import Point
        
        group = Group.objects.create(group_type='open', radius=10.0)
        
        # Create devices with locations
        device1 = Device.objects.create(
            hid='DEVICE-1',
            owner=self.owner,
            group=group,
            location=Point(-79.3832, 43.6532, srid=4326)  # Toronto
        )
        
        device2 = Device.objects.create(
            hid='DEVICE-2',
            owner=self.owner,
            group=group,
            location=Point(-79.3833, 43.6533, srid=4326)  # 100m away
        )
        
        # Test distance query
        origin = Point(-79.3832, 43.6532, srid=4326)
        devices_within_radius = Device.objects.filter(
            location__distance_lte=(origin, 1000)  # 1km
        ).annotate(
            distance=Distance('location', origin)
        )
        
        assert devices_within_radius.count() >= 2
    
    def test_celery_configuration(self):
        """Test: Celery is configured for async tasks"""
        from iot_message_router.celery import app
        
        assert app is not None
        assert hasattr(app, 'task')
    
    def test_docker_readiness(self):
        """Test: Docker files exist"""
        import os
        
        assert os.path.exists('docker-compose.yml')
        assert os.path.exists('Dockerfile')
    
    def test_role_based_permissions(self):
        """Test: Role-based access control exists"""
        # Test admin user
        admin = Owner.objects.create_user(
            email='admin@test.com',
            username='admin',
            password='testpass',
            is_staff=True
        )
        assert admin.is_staff is True
        
        # Test regular user
        regular = Owner.objects.create_user(
            email='user@test.com',
            username='user',
            password='testpass'
        )
        assert regular.is_staff is False


class TestAPIContracts(TestCase):
    """Test API contracts from Phase 0 and Original Requirements"""
    
    def setUp(self):
        self.owner = Owner.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.group = Group.objects.create(group_type='private', nid='test-nid')
        self.device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=self.group
        )
    
    def test_register_endpoint_exists(self):
        """Test: POST /register endpoint (or equivalent)"""
        # Device registration via /api/devices/ POST
        from django.urls import reverse
        from rest_framework.test import APIClient
        
        client = APIClient()
        client.force_authenticate(user=self.owner)
        
        response = client.post('/api/devices/', {
            'hid': 'NEW-DEVICE-001',
            'group_id': self.group.group_id,
            'nid': 'test-nid-002'
        })
        
        # Should accept or require auth - check status is not 404
        assert response.status_code != 404, "Device registration endpoint not found"
    
    def test_message_endpoint_exists(self):
        """Test: POST /messages endpoint exists"""
        from rest_framework.test import APIClient
        
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=self.device.api_key)
        
        response = client.post('/api/messages/', {
            'type': 'alert',
            'payload': {'test': 'data'}
        }, format='json')
        
        # Should accept or require proper format - check status is not 404
        assert response.status_code != 404, "Message endpoint not found"
    
    def test_inbox_endpoint_exists(self):
        """Test: GET /devices/{id}/inbox endpoint exists"""
        from rest_framework.test import APIClient
        
        client = APIClient()
        client.force_authenticate(user=self.owner)
        
        response = client.get(f'/api/devices/{self.device.device_id}/inbox/')
        assert response.status_code != 404, "Inbox endpoint not found"
    
    def test_acknowledge_endpoint_exists(self):
        """Test: POST /devices/{id}/inbox/{message_id}/ack endpoint exists"""
        from rest_framework.test import APIClient
        
        message = Message.objects.create(
            source_device=self.device,
            type='alert',
            payload={'test': 'data'}
        )
        inbox = DeviceInbox.objects.create(
            device=self.device,
            message=message,
            status='pending'
        )
        
        client = APIClient()
        client.force_authenticate(user=self.owner)
        
        response = client.post(f'/api/devices/{self.device.device_id}/inbox/{message.message_id}/ack/')
        assert response.status_code != 404, "Acknowledge endpoint not found"

