"""
Management command to create sample data for testing
Creates ONE sample of each entity with proper relationships
"""
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from accounts.models import Owner
from devices.models import Device
from messages.models import Group, Message, DeviceInbox, GroupType, InboxStatus, MessageType
from django.utils import timezone
from django.db import transaction


class Command(BaseCommand):
    help = 'Clear all data and create ONE sample of each entity with proper relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-all',
            action='store_true',
            help='Clear ALL existing data (not just sample data)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Clear all existing data
        self.stdout.write(self.style.WARNING('⚠️  Clearing ALL existing data...'))
        DeviceInbox.objects.all().delete()
        Message.objects.all().delete()
        Device.objects.all().delete()
        Group.objects.all().delete()
        Owner.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✅ All data cleared'))

        # Create ONE of each Group Type
        self.stdout.write('\n📦 Creating Groups (one of each type)...')
        groups = {}
        group_configs = {
            'private': {'nid': '0x123456', 'radius': None, 'description': 'Private group with NID filtering'},
            'exclusive': {'nid': '0x789ABC', 'radius': None, 'description': 'Exclusive group with NID filtering'},
            'open': {'nid': None, 'radius': 5.0, 'description': 'Open group with distance filtering'},
            'data_logging': {'nid': '0xDEF123', 'radius': None, 'description': 'Data logging group with NID'},
            'enhanced': {'nid': '0x456789', 'radius': 10.0, 'description': 'Enhanced group with both NID and distance'},
            'location': {'nid': '0xFFFFFFFF', 'radius': 15.0, 'description': 'Location group with broadcast NID and distance (32-bit)'},
        }
        
        for group_type, config in group_configs.items():
            group = Group.objects.create(
                group_type=group_type,
                nid=config['nid'],
                radius=config['radius'],
                description=config['description']
            )
            groups[group_type] = group
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created {group.get_group_type_display()} group (ID: {group.group_id})'))

        # Create ONE Admin User
        self.stdout.write('\n👤 Creating Users...')
        admin = Owner.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
            active=True
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created admin user: {admin.username} (password: admin123)'))

        # Create ONE Regular User
        regular_user = Owner.objects.create_user(
            username='demo_user',
            email='demo@example.com',
            password='demo123',
            first_name='Demo',
            last_name='User',
            is_staff=False,
            is_superuser=False,
            active=True
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created regular user: {regular_user.username} (password: demo123)'))

        # Create additional users for device associations (max 6 per device)
        additional_users = []
        for i in range(1, 4):  # Create 3 more users
            user = Owner.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='user123',
                first_name=f'User',
                last_name=f'{i}',
                is_staff=False,
                is_superuser=False,
                active=True
            )
            additional_users.append(user)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created user: {user.username} (password: user123)'))

        # Create TWO Devices in the same group for routing demonstration
        self.stdout.write('\n📱 Creating Devices...')
        
        # Device 1: Source device
        device1 = Device.objects.create(
            hid='DEMO-DEVICE-001',
            owner=regular_user,
            group=groups['enhanced'],  # Use enhanced group (has both NID and distance)
            nid='0x456789',
            webhook_url='https://webhook.example.com/demo-device-001',
            retry_limit=3,
            active=True
        )
        device1.set_location(43.6532, -79.3832)  # Toronto coordinates
        
        # Associate users with device1 (max 6)
        device1.add_user(admin)
        device1.add_user(additional_users[0])
        device1.add_user(additional_users[1])
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created device: {device1.hid}'))
        self.stdout.write(f'     Owner: {device1.owner.username}')
        self.stdout.write(f'     Group: {device1.group.get_group_type_display()}')
        self.stdout.write(f'     Associated Users: {device1.users.count()}/6 ({", ".join([u.username for u in device1.users.all()])})')
        self.stdout.write(f'     Location: {device1.location.y:.4f}, {device1.location.x:.4f}')
        self.stdout.write(f'     API Key: {device1.api_key}')
        
        # Device 2: Target device (same group, same NID, within distance)
        device2 = Device.objects.create(
            hid='DEMO-DEVICE-002',
            owner=admin,
            group=groups['enhanced'],  # Same group
            nid='0x456789',  # Same NID
            webhook_url='https://webhook.example.com/demo-device-002',
            retry_limit=3,
            active=True
        )
        device2.set_location(43.6533, -79.3833)  # Very close to device1 (within 10km radius)
        
        # Associate users with device2
        device2.add_user(regular_user)
        device2.add_user(additional_users[2])
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created device: {device2.hid}'))
        self.stdout.write(f'     Owner: {device2.owner.username}')
        self.stdout.write(f'     Group: {device2.group.get_group_type_display()}')
        self.stdout.write(f'     Associated Users: {device2.users.count()}/6 ({", ".join([u.username for u in device2.users.all()])})')
        self.stdout.write(f'     Location: {device2.location.y:.4f}, {device2.location.x:.4f}')
        self.stdout.write(f'     API Key: {device2.api_key}')
        
        # Use device1 as the source device for messages
        device = device1

        # Create ONE Alert Message
        self.stdout.write('\n📨 Creating Messages...')
        alert_message = Message.objects.create(
            type=MessageType.ALERT,
            alert_type='sensor',
            payload={
                'type': 'sensor',
                'temperature': 24.5,
                'humidity': 60,
                'battery': 85,
                'status': 'ok',
                'timestamp': timezone.now().isoformat(),
                'position': {
                    'latitude': 43.6532,
                    'longitude': -79.3832
                }
            },
            source_device=device,
            timestamp=timezone.now()
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created ALERT message (ID: {alert_message.message_id})'))
        self.stdout.write(f'     Type: Sensor Alert')
        self.stdout.write(f'     Payload: Temperature: 24.5°C, Humidity: 60%, Battery: 85%')

        # Create ONE Alarm Message
        alarm_message = Message.objects.create(
            type=MessageType.ALARM,
            alarm_type='pa',
            payload={
                'type': 'pa',
                'message': 'Public Address alarm triggered',
                'status': 'critical',
                'timestamp': timezone.now().isoformat(),
                'position': {
                    'latitude': 43.6532,
                    'longitude': -79.3832
                }
            },
            source_device=device,
            timestamp=timezone.now()
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created ALARM message (ID: {alarm_message.message_id})'))
        self.stdout.write(f'     Type: Public Address Alarm')
        self.stdout.write(f'     Payload: Critical status alarm')

        # Route messages to create inbox entries
        self.stdout.write('\n🔄 Routing Messages...')
        from messages.services import MessageRoutingService
        
        # Route alert message
        try:
            alert_inbox_entries = MessageRoutingService.route_message(alert_message, device)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Alert message routed to {len(alert_inbox_entries)} device(s)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Alert routing failed: {e}'))

        # Route alarm message
        try:
            alarm_inbox_entries = MessageRoutingService.route_message(alarm_message, device)
            self.stdout.write(self.style.SUCCESS(f'  ✓ Alarm message routed to {len(alarm_inbox_entries)} device(s)'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Alarm routing failed: {e}'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n✅ Sample data creation complete!'))
        self.stdout.write('\n📊 Summary:')
        self.stdout.write(f'  • Groups: {Group.objects.count()} (one of each type)')
        self.stdout.write(f'  • Users: {Owner.objects.count()} (1 admin, {Owner.objects.filter(is_staff=False).count()} regular)')
        self.stdout.write(f'  • Devices: {Device.objects.count()}')
        self.stdout.write(f'  • Messages: {Message.objects.count()} (1 alert, 1 alarm)')
        self.stdout.write(f'  • Inbox Entries: {DeviceInbox.objects.count()}')
        
        self.stdout.write('\n🔐 Login Credentials:')
        self.stdout.write('  Admin: admin / admin123')
        self.stdout.write('  Demo User: demo_user / demo123')
        self.stdout.write('  Additional Users: user1, user2, user3 / user123')
        
        self.stdout.write('\n📱 Device Information:')
        self.stdout.write(f'  HID: {device.hid}')
        self.stdout.write(f'  API Key: {device.api_key}')
        self.stdout.write(f'  Group: {device.group.get_group_type_display()}')
        self.stdout.write(f'  Associated Users: {device.users.count()}/6')
