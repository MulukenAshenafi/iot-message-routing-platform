from rest_framework import serializers
from messages.models import Message, DeviceInbox, Group
from django.utils import timezone
from datetime import datetime


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['group_id', 'group_type', 'nid', 'radius', 'description', 'created_at']
        read_only_fields = ['group_id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    """Message serializer matching specification format"""
    source_device_hid = serializers.CharField(source='source_device.hid', read_only=True)
    
    # Specification-compliant fields
    self = serializers.SerializerMethodField()
    hid = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    tt = serializers.SerializerMethodField()
    tt_string = serializers.SerializerMethodField()
    msg = serializers.SerializerMethodField()  # payload as 'msg'
    lrt = serializers.SerializerMethodField()
    lmr = serializers.SerializerMethodField()
    ae = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'self', 'message_id', 'id', 'type', 'hid', 'bcname', 'to', 'co', 'tt', 'tt_string',
            'alert_type', 'alarm_type', 'payload', 'msg', 'source_device', 'source_device_hid',
            'timestamp', 'user', 'read', 'last_read_at', 'last_modified_read',
            'lrt', 'lmr', 'ae', 'acknowledge_status', 'owner'
        ]
        read_only_fields = ['message_id', 'timestamp', 'id', 'tt', 'tt_string', 'hid']
    
    def get_self(self, obj):
        """Generate self link: /messages/{hid}/{id}"""
        return f"/messages/hid/{obj.source_device.hid}/{obj.message_id}"
    
    def get_id(self, obj):
        """Return message_id as 'id'"""
        return obj.message_id
    
    def get_hid(self, obj):
        """Return source device HID"""
        return obj.source_device.hid
    
    def get_tt(self, obj):
        """Return timestamp as Unix timestamp (tt)"""
        if obj.timestamp:
            return obj.timestamp.timestamp()
        return None
    
    def get_tt_string(self, obj):
        """Return formatted timestamp string (tt_string)"""
        if obj.timestamp:
            # Format: "12:18AM Sep 2, 2025"
            return obj.timestamp.strftime("%I:%M%p %b %d, %Y")
        return None
    
    def get_msg(self, obj):
        """Return payload as 'msg'"""
        return obj.payload
    
    def get_lrt(self, obj):
        """Return last read timestamp (lrt) as string"""
        if obj.last_read_at:
            return obj.last_read_at.strftime("%I:%M%p %b %d, %Y")
        return None
    
    def get_lmr(self, obj):
        """Return last modified read timestamp (lmr) as string"""
        if obj.last_modified_read:
            return obj.last_modified_read.strftime("%I:%M%p %b %d, %Y")
        return None
    
    def get_ae(self, obj):
        """Return acknowledge status (ae)"""
        if obj.acknowledge_status:
            return obj.acknowledge_status
        # Check from inbox status if available
        inbox_entries = obj.inbox_entries.all()
        if inbox_entries.exists():
            # Return status of first inbox entry
            status = inbox_entries.first().status
            if status == 'acknowledged':
                return 'YES'
            elif status == 'pending':
                return 'PENDING'
            return 'NO'
        return 'NO'
    
    def get_owner(self, obj):
        """Generate owner object with self link"""
        if obj.source_device and obj.source_device.owner:
            return {
                'self': f"/devices/{obj.source_device.hid}"
            }
        return None
    
    def to_representation(self, instance):
        """Transform response to match specification format with hyphenated field names"""
        data = super().to_representation(instance)
        
        # Ensure payload is also available as 'msg' (already handled by get_msg)
        # But keep payload for backward compatibility if needed
        if 'payload' in data and 'msg' in data:
            # Both are present, which is fine
            pass
        
        return data


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating messages from device"""
    type = serializers.ChoiceField(choices=['alert', 'alarm'])
    payload = serializers.JSONField()
    user = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def create(self, validated_data):
        # Source device is set in the view
        source_device = validated_data.pop('source_device')
        
        # Extract fields from payload per specification
        payload = validated_data.get('payload', {})
        bcname = payload.get('bcname') or payload.get('bc_name')
        to_field = payload.get('to')
        co_field = payload.get('co')
        
        # Extract user from payload if not provided directly
        user_field = validated_data.get('user') or payload.get('user')
        
        # Determine alert/alarm type from payload
        alert_type = None
        alarm_type = None
        
        if validated_data['type'] == 'alert':
            # Extract alert type from payload if available
            msg_type = payload.get('type', '').upper()
            if msg_type in ['SENSOR', 'PANIC', 'NS-PANIC', 'UNKNOWN', 'DISTRESS']:
                alert_type = msg_type.lower().replace('-', '_')
        elif validated_data['type'] == 'alarm':
            msg_type = payload.get('type', '').upper()
            if msg_type in ['PA', 'PM', 'SERVICE', 'SERVICE-CHILDCARE']:
                # Handle SERVICE-CHILDCARE and similar variations
                if '-' in msg_type:
                    alarm_type = msg_type.lower().split('-')[0]
                else:
                    alarm_type = msg_type.lower()
        
        # Create message with extracted fields
        message = Message.objects.create(
            source_device=source_device,
            type=validated_data['type'],
            payload=payload,
            alert_type=alert_type,
            alarm_type=alarm_type,
            bcname=bcname,
            to=to_field,
            co=co_field,
            user=user_field
        )
        return message


class DeviceInboxSerializer(serializers.ModelSerializer):
    """Device Inbox serializer matching specification format"""
    message = serializers.SerializerMethodField()
    device_hid = serializers.CharField(source='device.hid', read_only=True)
    hid = serializers.SerializerMethodField()
    read = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceInbox
        fields = [
            'id', 'device', 'device_hid', 'hid', 'message', 'status',
            'delivery_attempts', 'created_at', 'delivered_at', 'acknowledged_at',
            'read'
        ]
        read_only_fields = ['id', 'created_at', 'delivered_at', 'acknowledged_at']
    
    def get_message(self, obj):
        """Return message with proper serializer context"""
        serializer = MessageSerializer(obj.message, context=self.context)
        return serializer.data
    
    def get_hid(self, obj):
        """Return device HID"""
        return obj.device.hid if obj.device else None
    
    def get_read(self, obj):
        """Return message read status"""
        if obj.message:
            return obj.message.read
        return False
    
    def to_representation(self, instance):
        """Transform response to match specification format"""
        data = super().to_representation(instance)
        
        # If message is nested, ensure it has proper format
        if 'message' in data and isinstance(data['message'], dict):
            msg_data = data['message']
            # Ensure message has all spec fields
            if 'id' not in msg_data and 'message_id' in msg_data:
                msg_data['id'] = msg_data['message_id']
            if 'read' not in msg_data:
                msg_data['read'] = self.get_read(instance)
        
        return data
