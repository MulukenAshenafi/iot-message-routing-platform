from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.gis.geos import Point
from messages.models import Message, DeviceInbox, Group
from messages.serializers import MessageSerializer, MessageCreateSerializer, DeviceInboxSerializer, GroupSerializer
from messages.services import MessageRoutingService
from devices.models import Device
from api.permissions import DeviceAPIKeyAuthentication


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Message management
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Allow API key authentication for POST requests
        """
        if self.action in ['messages_by_hid'] and self.request.method == 'POST':
            # Allow both authenticated users and API key for POST
            return [AllowAny()]  # We'll check auth manually
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """
        Filter messages by user's devices if not admin
        """
        user = self.request.user
        if user.is_staff:
            return Message.objects.all()
        # Return messages from user's devices
        user_device_ids = user.devices.values_list('device_id', flat=True)
        return Message.objects.filter(source_device_id__in=user_device_ids)
    
    @action(detail=False, methods=['get', 'post'], url_path='hid/(?P<hid>[^/.]+)')
    def messages_by_hid(self, request, hid=None):
        """
        Get all messages for a device by HID or create message for device by HID
        GET /api/messages/hid/{hid}/?startIndex=0&size=20
        POST /api/messages/hid/{hid}/
        """
        try:
            device = Device.objects.get(hid=hid, active=True)
            
            # For POST requests, allow device API key authentication
            authenticated_via_api_key = False
            if request.method == 'POST':
                device_auth = DeviceAPIKeyAuthentication()
                try:
                    auth_result = device_auth.authenticate(request)
                    if auth_result and auth_result[0] == device:
                        # Device authenticated via API key, proceed
                        authenticated_via_api_key = True
                except:
                    pass
                
                if not authenticated_via_api_key:
                    # Fall back to user authentication
                    if not request.user.is_authenticated:
                        return Response(
                            {'error': 'Authentication required. Provide X-API-Key header or JWT token.'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    elif not (request.user == device.owner or request.user.is_staff):
                        return Response(
                            {'error': 'Permission denied'},
                            status=status.HTTP_403_FORBIDDEN
                        )
            else:
                # For GET requests, check user permission
                if not (request.user.is_authenticated and (request.user == device.owner or request.user.is_staff)):
                    return Response(
                        {'error': 'Permission denied'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            if request.method == 'GET':
                # Get messages for this device
                queryset = Message.objects.filter(source_device=device).order_by('-timestamp')
                
                # Pagination support (startIndex and size)
                start_index = int(request.query_params.get('startIndex', 0))
                size = int(request.query_params.get('size', 20))
                
                total = queryset.count()
                messages = queryset[start_index:start_index + size]
                
                serializer = MessageSerializer(messages, many=True, context={'request': request})
                return Response({
                    'total': total,
                    'startIndex': start_index,
                    'size': size,
                    'messages': serializer.data
                })
            elif request.method == 'POST':
                # Create message for this device
                serializer = MessageCreateSerializer(data=request.data)
                if serializer.is_valid():
                    message = serializer.save(source_device=device)
                    
                    # Extract location from payload if available
                    payload = serializer.validated_data.get('payload', {})
                    position = payload.get('position', {})
                    if position and 'latitude' in position and 'longitude' in position:
                        lat = position['latitude']
                        lon = position['longitude']
                        if not device.location:
                            device.set_location(lat, lon)
                        elif device.location.y != lat or device.location.x != lon:
                            device.set_location(lat, lon)
                    
                    # Route message to target devices
                    try:
                        inbox_entries = MessageRoutingService.route_message(message, device)
                        
                        # Build detailed response
                        response_data = {
                            'message_id': str(message.message_id),
                            'status': 'routed' if inbox_entries else 'created',
                            'target_devices': len(inbox_entries),
                            'inbox_entries': [entry.id for entry in inbox_entries],
                            'message_type': message.type,
                            'source_device': device.hid
                        }
                        
                        # Add target device details if any
                        if inbox_entries:
                            response_data['target_device_hids'] = [entry.device.hid for entry in inbox_entries]
                        else:
                            # Provide helpful information about why no targets
                            from devices.models import Device as DeviceModel
                            same_group = DeviceModel.objects.filter(group=device.group, active=True).exclude(device_id=device.device_id)
                            response_data['warning'] = f'No target devices found. {same_group.count()} other device(s) in same group.'
                            if device.group.uses_nid():
                                response_data['nid_info'] = {
                                    'device_nid': device.nid,
                                    'group_nid': device.group.nid,
                                    'message_nid': message.payload.get('nid') or device.nid
                                }
                        
                        return Response(response_data, status=status.HTTP_201_CREATED)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        return Response(
                            {
                                'error': f'Message created but routing failed: {str(e)}',
                                'message_id': str(message.message_id),
                                'status': 'created_but_routing_failed'
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], url_path='hid/(?P<hid>[^/.]+)/(?P<message_id>[^/.]+)')
    def message_by_hid_and_id(self, request, hid=None, message_id=None):
        """
        Get a specific message for a device by HID and message ID
        GET /api/messages/hid/{hid}/{id}
        """
        try:
            device = Device.objects.get(hid=hid, active=True)
            
            # Check permission
            if not (request.user == device.owner or request.user.is_staff):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            message = Message.objects.get(message_id=message_id, source_device=device)
            serializer = MessageSerializer(message, context={'request': request})
            return Response(serializer.data)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['patch'], url_path='hid/(?P<hid>[^/.]+)/(?P<message_id>[^/.]+)')
    def update_message_by_hid(self, request, hid=None, message_id=None):
        """
        Update a specific message for a device by HID and message ID
        PATCH /api/messages/hid/{hid}/{id}
        """
        try:
            device = Device.objects.get(hid=hid, active=True)
            
            # Check permission
            if not (request.user == device.owner or request.user.is_staff):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            message = Message.objects.get(message_id=message_id, source_device=device)
            serializer = MessageSerializer(message, data=request.data, partial=True, context={'request': request})
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['delete'], url_path='hid/(?P<hid>[^/.]+)/(?P<message_id>[^/.]+)')
    def delete_message_by_hid(self, request, hid=None, message_id=None):
        """
        Delete a specific message for a device by HID and message ID
        DELETE /api/messages/hid/{hid}/{id}
        """
        try:
            device = Device.objects.get(hid=hid, active=True)
            
            # Check permission
            if not (request.user == device.owner or request.user.is_staff):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            message = Message.objects.get(message_id=message_id, source_device=device)
            message.delete()
            return Response({'message': 'Message deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def create(self, request, *args, **kwargs):
        """
        Create a new message and route it to target devices
        POST /api/messages/
        
        Authentication: Device API key (X-API-Key header)
        """
        # Try to authenticate using device API key
        device_auth = DeviceAPIKeyAuthentication()
        device = device_auth.authenticate(request)
        
        if device:
            # Device authentication successful
            source_device = device[0]
        else:
            # Try user authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required. Provide X-API-Key header or JWT token.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            # For user authentication, we need to get device from request
            # This assumes device_id is in the payload
            device_id = request.data.get('device_id')
            if not device_id:
                return Response(
                    {'error': 'device_id required when using user authentication'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                source_device = Device.objects.get(device_id=device_id, owner=request.user)
            except Device.DoesNotExist:
                return Response(
                    {'error': 'Device not found or access denied'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Validate and create message
        serializer = MessageCreateSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save(source_device=source_device)
            
            # Extract location from payload if available
            payload = serializer.validated_data.get('payload', {})
            position = payload.get('position', {})
            if position and 'latitude' in position and 'longitude' in position:
                lat = position['latitude']
                lon = position['longitude']
                if not source_device.location:
                    source_device.set_location(lat, lon)
                elif source_device.location.y != lat or source_device.location.x != lon:
                    # Update location if different
                    source_device.set_location(lat, lon)
            
            # Route message to target devices
            try:
                inbox_entries = MessageRoutingService.route_message(message, source_device)
                
                return Response({
                    'message_id': message.message_id,
                    'status': 'routed',
                    'target_devices': len(inbox_entries),
                    'inbox_entries': [entry.id for entry in inbox_entries]
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error': f'Message created but routing failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Group management
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def network_devices_by_hid(request, hid):
    """
    Get all devices within network range for a device by HID
    GET /api/network/hid/{hid}/
    """
    try:
        device = Device.objects.get(hid=hid, active=True)
        
        # Check permission
        if not (request.user == device.owner or request.user.is_staff):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        network_devices = MessageRoutingService.get_devices_in_network_range(device)
        from devices.serializers import DeviceSerializer
        serializer = DeviceSerializer(network_devices, many=True, context={'request': request})
        return Response(serializer.data)
    except Device.DoesNotExist:
        return Response(
            {'error': 'Device not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def network_owners_by_owner_id(request, owner_id):
    """
    Get all owners within network range
    GET /api/network/owners/{owner_id}/
    """
    if request.user.id != owner_id and not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    owners = MessageRoutingService.get_owners_in_network_range(owner_id)
    from accounts.serializers import OwnerSerializer
    serializer = OwnerSerializer(owners, many=True, context={'request': request})
    return Response(serializer.data)
