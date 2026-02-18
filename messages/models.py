from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point


class GroupType(models.TextChoices):
    PRIVATE = 'private', 'Private'
    EXCLUSIVE = 'exclusive', 'Exclusive'
    OPEN = 'open', 'Open'
    DATA_LOGGING = 'data_logging', 'Data-Logging'
    ENHANCED = 'enhanced', 'Enhanced'
    LOCATION = 'location', 'Location'


class Group(models.Model):
    """Group model defining message routing rules"""
    group_id = models.AutoField(primary_key=True)
    group_type = models.CharField(max_length=20, choices=GroupType.choices)
    nid = models.CharField(max_length=100, blank=True, null=True, help_text="Network ID")
    radius = models.FloatField(blank=True, null=True, help_text="Radius in kilometers")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'groups'
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'
    
    def __str__(self):
        return f"{self.get_group_type_display()} - {self.nid or 'No NID'}"
    
    def uses_nid(self):
        """Check if this group type uses NID"""
        return self.group_type in [
            GroupType.PRIVATE, 
            GroupType.EXCLUSIVE, 
            GroupType.DATA_LOGGING, 
            GroupType.ENHANCED, 
            GroupType.LOCATION
        ]
    
    def uses_distance(self):
        """Check if this group type uses distance"""
        return self.group_type in [
            GroupType.OPEN, 
            GroupType.ENHANCED, 
            GroupType.LOCATION
        ]


class MessageType(models.TextChoices):
    ALERT = 'alert', 'Alert'
    ALARM = 'alarm', 'Alarm'


class AlertType(models.TextChoices):
    SENSOR = 'sensor', 'Sensor'
    PANIC = 'panic', 'Panic'
    NS_PANIC = 'ns-panic', 'NS-Panic'
    UNKNOWN = 'unknown', 'Unknown'
    DISTRESS = 'distress', 'Distress'


class AlarmType(models.TextChoices):
    PA = 'pa', 'PA'
    PM = 'pm', 'PM'
    SERVICE = 'service', 'Service'


class Message(models.Model):
    """Message model storing incoming messages"""
    message_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=10, choices=MessageType.choices)
    alert_type = models.CharField(max_length=20, choices=AlertType.choices, blank=True, null=True)
    alarm_type = models.CharField(max_length=20, choices=AlarmType.choices, blank=True, null=True)
    payload = models.JSONField(default=dict, help_text="Message payload stored as JSON (also accessible as 'msg')")
    source_device = models.ForeignKey('devices.Device', on_delete=models.CASCADE, related_name='sent_messages')
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Message timestamp (also accessible as 'tt')")
    user = models.CharField(max_length=100, blank=True, null=True)
    # Additional fields from specification
    bcname = models.CharField(max_length=200, blank=True, null=True, help_text="Broadcast name")
    to = models.CharField(max_length=200, blank=True, null=True, help_text="Recipient")
    co = models.CharField(max_length=200, blank=True, null=True, help_text="Contact/Coordinator")
    read = models.BooleanField(default=False, help_text="Message read status")
    last_read_at = models.DateTimeField(blank=True, null=True, help_text="Last read timestamp (lrt)")
    last_modified_read = models.DateTimeField(blank=True, null=True, help_text="Last modified read timestamp (lmr)")
    acknowledge_status = models.CharField(max_length=20, blank=True, null=True, help_text="Acknowledge status (ae) - YES/NO/PENDING")
    
    class Meta:
        db_table = 'messages'
        ordering = ['-timestamp']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
    
    def __str__(self):
        return f"Message {self.message_id} - {self.type} from {self.source_device.hid}"
    
    def is_alarm(self):
        """Check if message is high priority alarm"""
        return self.type == MessageType.ALARM


class InboxStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    DELIVERED = 'delivered', 'Delivered'
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
    FAILED = 'failed', 'Failed'


class DeviceInbox(models.Model):
    """Device inbox queue - stores messages for each device"""
    id = models.AutoField(primary_key=True)
    device = models.ForeignKey('devices.Device', on_delete=models.CASCADE, related_name='inbox_messages')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='inbox_entries')
    status = models.CharField(max_length=20, choices=InboxStatus.choices, default=InboxStatus.PENDING)
    delivery_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'device_inbox'
        unique_together = ['device', 'message']
        indexes = [
            models.Index(fields=['device', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
        verbose_name = 'Device Inbox'
        verbose_name_plural = 'Device Inboxes'
    
    def __str__(self):
        return f"Inbox {self.id} - Device {self.device.hid} - {self.status}"
