from django.contrib import admin
from messages.models import Message, DeviceInbox, Group


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['group_id', 'group_type', 'nid', 'radius', 'created_at']
    list_filter = ['group_type', 'created_at']
    search_fields = ['nid', 'description']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'type', 'source_device', 'timestamp', 'user']
    list_filter = ['type', 'timestamp']
    search_fields = ['source_device__hid', 'user']
    readonly_fields = ['message_id', 'timestamp']
    ordering = ['-timestamp']


@admin.register(DeviceInbox)
class DeviceInboxAdmin(admin.ModelAdmin):
    list_display = ['id', 'device', 'message', 'status', 'delivery_attempts', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['device__hid', 'message__message_id']
    readonly_fields = ['created_at', 'delivered_at', 'acknowledged_at']
    ordering = ['-created_at']
