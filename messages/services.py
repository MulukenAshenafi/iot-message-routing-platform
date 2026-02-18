"""
Message Routing Service - Implements the 5-step routing algorithm
"""
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Q
from devices.models import Device
from messages.models import Message, DeviceInbox, InboxStatus
from messages.utils import nid_variants


class MessageRoutingService:
    """Service for routing messages to target devices using 5-step algorithm"""
    
    @staticmethod
    def route_message(message: Message, source_device: Device):
        """
        Route message to appropriate target devices using 5-step algorithm
        
        Step 1: Group Filtering
        Step 2: NID Filtering (if applicable)
        Step 3: Distance Filtering (if applicable)
        Step 4: Intersection Logic
        Step 5: Inbox Population
        """
        group = source_device.group
        
        # Step 1: Group Filtering
        # Find all devices belonging to the message's group
        candidates = Device.objects.filter(
            group=group,
            active=True
        ).exclude(device_id=source_device.device_id)
        
        # Step 2: NID Filtering (if applicable)
        if group.uses_nid():
            message_nid = message.payload.get('nid') or source_device.nid
            nid_values = nid_variants(message_nid)
            broadcast_values = ['0xFFFFFFFF', '0xffffffff', str(0xFFFFFFFF)]
            if nid_values:
                nid_filter = Q(nid__in=nid_values) | Q(nid__in=broadcast_values)
                candidates = candidates.filter(nid_filter)
        
        # Step 3: Distance Filtering (if applicable)
        if group.uses_distance() and source_device.location:
            radius_km = source_device.owner.radius_km if source_device.owner and source_device.owner.radius_km is not None else group.radius
            if radius_km is not None:
                radius_meters = radius_km * 1000  # Convert km to meters
                
                # PostGIS distance query
                # ST_Distance returns distance in meters for SRID 4326
                candidates = candidates.annotate(
                    distance=Distance('location', source_device.location)
                ).filter(distance__lte=radius_meters)
        
        # Step 4 & 5: Intersection logic and inbox population
        target_devices = list(candidates)
        
        # Prioritize alarms over alerts
        inbox_entries = []
        for device in target_devices:
            inbox_entry = DeviceInbox.objects.create(
                device=device,
                message=message,
                status=InboxStatus.PENDING
            )
            inbox_entries.append(inbox_entry)
            
            # Trigger webhook if configured
            if device.webhook_url:
                from messages.tasks import deliver_webhook
                # Prioritize alarms - deliver immediately
                if message.is_alarm():
                    deliver_webhook.delay(inbox_entry.id)
                else:
                    # Alerts can be queued
                    deliver_webhook.apply_async(args=[inbox_entry.id])
        
        return inbox_entries
    
    @staticmethod
    def get_devices_in_network_range(device: Device):
        """
        Get all devices within network range for a given device
        Based on group type and routing rules
        """
        group = device.group
        
        # Start with group filtering
        candidates = Device.objects.filter(
            group=group,
            active=True
        )
        
        # Apply NID filter if applicable
        if group.uses_nid() and device.nid:
            nid_values = nid_variants(device.nid)
            broadcast_values = ['0xFFFFFFFF', '0xffffffff', str(0xFFFFFFFF)]
            if nid_values:
                candidates = candidates.filter(
                    Q(nid__in=nid_values) | Q(nid__in=broadcast_values)
                )
        
        # Apply distance filter if applicable
        if group.uses_distance() and device.location:
            radius_km = device.owner.radius_km if device.owner and device.owner.radius_km is not None else group.radius
            if radius_km is None:
                return candidates.exclude(device_id=device.device_id)
            radius_meters = radius_km * 1000
            candidates = candidates.annotate(
                distance=Distance('location', device.location)
            ).filter(distance__lte=radius_meters)
        
        return candidates.exclude(device_id=device.device_id)
    
    @staticmethod
    def get_owners_in_network_range(owner_id: int):
        """
        Get all owners whose devices are within network range
        """
        from accounts.models import Owner
        
        try:
            owner = Owner.objects.get(id=owner_id)
            devices = owner.devices.filter(active=True)
            
            all_owners = set()
            for device in devices:
                network_devices = MessageRoutingService.get_devices_in_network_range(device)
                for network_device in network_devices:
                    all_owners.add(network_device.owner)
            
            return list(all_owners)
        except Owner.DoesNotExist:
            return []

