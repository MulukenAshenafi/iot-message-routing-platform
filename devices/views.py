from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from devices.models import Device
from devices.serializers import DeviceSerializer
from messages.serializers import DeviceInboxSerializer
from messages.models import DeviceInbox, InboxStatus
from api.permissions import DeviceAPIKeyAuthentication, IsDeviceOwner


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Device management
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter devices by owner or association (users list) if not admin
        Prefetch users for efficient loading
        """
        from django.db import models
        user = self.request.user
        queryset = Device.objects.prefetch_related('users', 'owner', 'group')
        if user.is_staff:
            return queryset.filter(active=True)
        # Return devices where user is owner OR user is in users list
        return queryset.filter(
            models.Q(owner=user) | models.Q(users=user),
            active=True
        ).distinct()
    
    def has_permission(self, device, user):
        """
        Check if user has permission to access device
        User must be owner, in users list, or admin
        """
        if user.is_staff:
            return True
        if user == device.owner:
            return True
        # Check if user is in the prefetched users list
        # Use prefetched list if available, otherwise check database
        if hasattr(device, '_prefetched_objects_cache') and 'users' in device._prefetched_objects_cache:
            return user in device._prefetched_objects_cache['users']
        # Fallback to database query if not prefetched
        return device.users.filter(pk=user.pk).exists()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new device with proper error handling
        """
        if getattr(request.user, 'parent_owner', None):
            return Response(
                {'error': 'Sub-users cannot register devices.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            # Include API key only at creation time
            response_data = serializer.data.copy()
            response_data['api-key'] = serializer.instance.api_key
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            # Handle validation errors and other exceptions
            if hasattr(serializer, '_errors'):
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {'error': str(e), 'detail': 'An error occurred while creating the device.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def perform_create(self, serializer):
        """
        Set owner to current user when creating device
        """
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'], url_path='inbox')
    def inbox(self, request, pk=None):
        """
        Get device inbox messages
        GET /api/devices/{id}/inbox/?user=xxx&nid=xxx&hid=xxx
        """
        device = self.get_object()
        
        # Check permission using helper method
        if not self.has_permission(device, request.user):
            return Response(
                {'error': 'Permission denied. You must be the owner or an associated user of this device.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = DeviceInbox.objects.filter(
            device=device,
            status=InboxStatus.PENDING
        ).select_related('message', 'device')
        
        # Apply filters
        user = request.query_params.get('user')
        if user:
            queryset = queryset.filter(message__user=user)
        
        nid = request.query_params.get('nid')
        if nid:
            queryset = queryset.filter(device__nid=nid)
        
        hid = request.query_params.get('hid')
        if hid:
            queryset = queryset.filter(device__hid=hid)
        
        serializer = DeviceInboxSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='inbox/(?P<message_id>[^/.]+)/ack')
    def acknowledge_message(self, request, pk=None, message_id=None):
        """
        Acknowledge message delivery
        POST /api/devices/{id}/inbox/{message_id}/ack/
        """
        device = self.get_object()
        
        # Check permission using helper method
        if not self.has_permission(device, request.user):
            return Response(
                {'error': 'Permission denied. You must be the owner or an associated user of this device.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            inbox_entry = DeviceInbox.objects.get(
                device=device,
                message_id=message_id
            )
            inbox_entry.status = InboxStatus.ACKNOWLEDGED
            inbox_entry.acknowledged_at = timezone.now()
            inbox_entry.save()
            
            # Update message fields per specification
            message = inbox_entry.message
            message.read = True
            if not message.last_read_at:
                message.last_read_at = timezone.now()
            message.last_modified_read = timezone.now()
            message.acknowledge_status = 'YES'
            message.save()
            
            return Response({
                'status': 'acknowledged',
                'message_id': message_id,
                'device_id': device.device_id,
                'ae': 'YES',
                'read': True
            })
        except DeviceInbox.DoesNotExist:
            return Response(
                {'error': 'Message not found in device inbox'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='hid/(?P<hid>[^/.]+)')
    def device_by_hid(self, request, hid=None):
        """
        Get device by HID
        GET /api/devices/hid/{hid}/
        """
        # Use get_queryset() to ensure proper filtering by permissions
        # get_queryset() already includes prefetch_related
        queryset = self.get_queryset()
        try:
            device = queryset.get(hid=hid)
            
            # Additional permission check using helper method (redundant but safe)
            if not self.has_permission(device, request.user):
                return Response(
                    {'error': 'Permission denied. You must be the owner or an associated user of this device.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = DeviceSerializer(device, context={'request': request})
            return Response(serializer.data)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found or you do not have permission to access it'},
                status=status.HTTP_404_NOT_FOUND
            )