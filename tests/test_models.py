"""
Model Tests
Tests for all database models
"""
import pytest
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from accounts.models import Owner
from devices.models import Device
from messages.models import Group, Message, DeviceInbox


class TestOwnerModel(TestCase):
    """Test Owner model"""
    
    def test_create_owner(self):
        """Test creating an owner"""
        owner = Owner.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        assert owner.email == 'test@example.com'
        assert owner.username == 'testuser'
        assert owner.check_password('testpass123')
    
    def test_owner_email_unique(self):
        """Test email must be unique"""
        Owner.objects.create_user(
            email='duplicate@example.com',
            username='user1',
            password='testpass123'
        )
        
        with pytest.raises(Exception):  # IntegrityError or ValidationError
            Owner.objects.create_user(
                email='duplicate@example.com',
                username='user2',
                password='testpass123'
            )


class TestDeviceModel(TestCase):
    """Test Device model"""
    
    def setUp(self):
        self.owner = Owner.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.group = Group.objects.create(group_type='private', nid='test-nid')
    
    def test_create_device(self):
        """Test creating a device"""
        device = Device.objects.create(
            hid='TEST-DEVICE-001',
            owner=self.owner,
            group=self.group,
            nid='test-nid-001',
            location=Point(-79.3832, 43.6532, srid=4326)
        )
        
        assert device.hid == 'TEST-DEVICE-001'
        assert device.owner == self.owner
        assert device.group == self.group
        assert device.api_key is not None
        assert len(device.api_key) > 0
    
    def test_device_api_key_generation(self):
        """Test API key is auto-generated"""
        device = Device.objects.create(
            hid='TEST-DEVICE-002',
            owner=self.owner,
            group=self.group
        )
        
        assert device.api_key is not None
        assert len(device.api_key) >= 32  # Should be at least 32 chars
    
    def test_device_api_key_verification(self):
        """Test API key verification"""
        device = Device.objects.create(
            hid='TEST-DEVICE-003',
            owner=self.owner,
            group=self.group
        )
        
        assert device.verify_api_key(device.api_key) is True
        assert device.verify_api_key('wrong-key') is False
    
    def test_device_max_users_limit(self):
        """Test MAX_USERS limit enforcement"""
        device = Device.objects.create(
            hid='TEST-DEVICE-004',
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
        
        # Add 6 users - should succeed
        for i in range(6):
            device.add_user(users[i])
        
        assert device.users.count() == 6
        
        # Try 7th - should fail
        with pytest.raises(ValueError, match='maximum of 6 users'):
            device.add_user(users[6])
    
    def test_device_set_location(self):
        """Test setting device location"""
        device = Device.objects.create(
            hid='TEST-DEVICE-005',
            owner=self.owner,
            group=self.group
        )
        
        device.set_location(43.6532, -79.3832)
        assert device.location is not None
        assert device.location.x == -79.3832  # Longitude
        assert device.location.y == 43.6532   # Latitude


class TestGroupModel(TestCase):
    """Test Group model"""
    
    def test_create_group(self):
        """Test creating a group"""
        group = Group.objects.create(
            group_type='enhanced',
            nid='test-nid-001',
            radius=10.0,
            description='Test Enhanced Group'
        )
        
        assert group.group_type == 'enhanced'
        assert group.nid == 'test-nid-001'
        assert group.radius == 10.0
    
    def test_all_group_types(self):
        """Test all group types can be created"""
        types = ['private', 'exclusive', 'open', 'data_logging', 'enhanced', 'location']
        
        for group_type in types:
            group = Group.objects.create(group_type=group_type)
            assert group.group_type == group_type


class TestMessageModel(TestCase):
    """Test Message model"""
    
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
    
    def test_create_alert_message(self):
        """Test creating an alert message"""
        message = Message.objects.create(
            source_device=self.device,
            type='alert',
            alert_type='sensor',
            payload={'temperature': 25.5, 'humidity': 60}
        )
        
        assert message.type == 'alert'
        assert message.alert_type == 'sensor'
        assert message.payload == {'temperature': 25.5, 'humidity': 60}
    
    def test_create_alarm_message(self):
        """Test creating an alarm message"""
        message = Message.objects.create(
            source_device=self.device,
            type='alarm',
            alarm_type='pa',
            payload={'alarm': 'intrusion_detected'}
        )
        
        assert message.type == 'alarm'
        assert message.alarm_type == 'pa'
        assert message.payload == {'alarm': 'intrusion_detected'}


class TestDeviceInboxModel(TestCase):
    """Test DeviceInbox model"""
    
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
        self.message = Message.objects.create(
            source_device=self.device,
            type='alert',
            payload={'test': 'data'}
        )
    
    def test_create_inbox_entry(self):
        """Test creating device inbox entry"""
        inbox = DeviceInbox.objects.create(
            device=self.device,
            message=self.message,
            status='pending'
        )
        
        assert inbox.device == self.device
        assert inbox.message == self.message
        assert inbox.status == 'pending'
    
    def test_inbox_status_choices(self):
        """Test inbox status choices"""
        statuses = [choice[0] for choice in DeviceInbox._meta.get_field('status').choices]
        assert 'pending' in statuses
        assert 'acknowledged' in statuses

