"""
API Endpoints Integration Tests

Tests all REST API endpoints to ensure they work correctly.
"""
import pytest
from django.test import TestCase
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Owner
from devices.models import Device
from messages.models import Message, Group, DeviceInbox


@pytest.mark.integration
@pytest.mark.django_db
class TestOwnerEndpoints(TestCase):
    """Test Owner API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.owner = Owner.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Owner'
        )
        self.token = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')
    
    def test_list_owners(self):
        """GET /api/owners/ - List all owners"""
        response = self.client.get('/api/owners/')
        assert response.status_code == 200
        assert isinstance(response.data, (list, dict))
    
    def test_create_owner(self):
        """POST /api/owners/ - Create new owner"""
        response = self.client.post('/api/owners/', {
            'email': 'newowner@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'Owner'
        }, format='json')
        assert response.status_code in [200, 201]
    
    def test_get_owner(self):
        """GET /api/owners/{id}/ - Get specific owner"""
        response = self.client.get(f'/api/owners/{self.owner.id}/')
        assert response.status_code == 200
        assert response.data['email'] == self.owner.email
    
    def test_update_owner(self):
        """PATCH /api/owners/{id}/ - Update owner"""
        response = self.client.patch(f'/api/owners/{self.owner.id}/', {
            'first_name': 'Updated'
        }, format='json')
        assert response.status_code == 200
        self.owner.refresh_from_db()
        assert self.owner.first_name == 'Updated'


@pytest.mark.integration
@pytest.mark.django_db
class TestDeviceEndpoints(TestCase):
    """Test Device API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.owner = Owner.objects.create_user(
            email='deviceowner@example.com',
            password='testpass123'
        )
        self.group = Group.objects.create(
            group_type='open',
            description='Test group'
        )
        self.token = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')
    
    def test_list_devices(self):
        """GET /api/devices/ - List devices"""
        response = self.client.get('/api/devices/')
        assert response.status_code == 200
    
    def test_create_device(self):
        """POST /api/devices/ - Create device"""
        response = self.client.post('/api/devices/', {
            'hid': 'NEW-DEVICE-001',
            'group_id': self.group.group_id,
            'location_lat': 40.7128,
            'location_lon': -74.0060,
            'retry_limit': 3
        }, format='json')
        assert response.status_code in [200, 201]
        assert 'api_key' in response.data
    
    def test_get_device(self):
        """GET /api/devices/{id}/ - Get device"""
        device = Device.objects.create(
            hid='TEST-DEV',
            owner=self.owner,
            group=self.group
        )
        response = self.client.get(f'/api/devices/{device.device_id}/')
        assert response.status_code == 200
        assert response.data['hid'] == device.hid
    
    def test_get_device_inbox(self):
        """GET /api/devices/{id}/inbox/ - Get device inbox"""
        device = Device.objects.create(
            hid='INBOX-DEV',
            owner=self.owner,
            group=self.group
        )
        message = Message.objects.create(
            type='alert',
            payload={'test': 'data'},
            source_device=device
        )
        DeviceInbox.objects.create(
            device=device,
            message=message,
            status='pending'
        )
        
        response = self.client.get(f'/api/devices/{device.device_id}/inbox/')
        assert response.status_code == 200
        assert len(response.data) > 0
    
    def test_acknowledge_message(self):
        """POST /api/devices/{id}/inbox/{message_id}/ack/ - Acknowledge message"""
        device = Device.objects.create(
            hid='ACK-DEV',
            owner=self.owner,
            group=self.group
        )
        message = Message.objects.create(
            type='alert',
            payload={'test': 'data'},
            source_device=device
        )
        inbox = DeviceInbox.objects.create(
            device=device,
            message=message,
            status='pending'
        )
        
        response = self.client.post(
            f'/api/devices/{device.device_id}/inbox/{message.message_id}/ack/',
            format='json'
        )
        assert response.status_code == 200
        
        inbox.refresh_from_db()
        assert inbox.status == 'acknowledged'


@pytest.mark.integration
@pytest.mark.django_db
class TestMessageEndpoints(TestCase):
    """Test Message API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.owner = Owner.objects.create_user(
            email='msgowner@example.com',
            password='testpass123'
        )
        self.group = Group.objects.create(group_type='open')
        self.device = Device.objects.create(
            hid='MSG-DEVICE',
            owner=self.owner,
            group=self.group
        )
        self.token = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token.access_token}')
    
    def test_list_messages(self):
        """GET /api/messages/ - List messages"""
        response = self.client.get('/api/messages/')
        assert response.status_code == 200
    
    def test_create_message_with_api_key(self):
        """POST /api/messages/hid/{hid}/ - Create message with API key"""
        client = APIClient()  # No JWT, use API key
        response = client.post(
            f'/api/messages/hid/{self.device.hid}/',
            {
                'type': 'alert',
                'payload': {'sensor': 'temperature', 'value': 25}
            },
            format='json',
            HTTP_X_API_KEY=self.device.api_key
        )
        assert response.status_code in [200, 201]
        assert 'message_id' in response.data or 'id' in response.data
    
    def test_get_messages_by_hid(self):
        """GET /api/messages/hid/{hid}/ - Get messages by device HID"""
        Message.objects.create(
            type='alert',
            payload={'test': 'data'},
            source_device=self.device
        )
        
        response = self.client.get(f'/api/messages/hid/{self.device.hid}/')
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

