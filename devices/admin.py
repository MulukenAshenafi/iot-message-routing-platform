from django.contrib import admin
from devices.models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['hid', 'owner', 'group', 'nid', 'active', 'created_at']
    list_filter = ['active', 'group', 'created_at']
    search_fields = ['hid', 'owner__email', 'nid']
    readonly_fields = ['api_key', 'api_key_hash', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Device Info', {
            'fields': ('hid', 'api_key', 'api_key_hash', 'owner', 'group', 'nid', 'active')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Webhook', {
            'fields': ('webhook_url', 'retry_limit')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
