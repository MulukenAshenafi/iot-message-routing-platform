from rest_framework import serializers
from devices.models import Device
from messages.serializers import GroupSerializer


# Minimal owner serializer for devices to avoid circular recursion
class DeviceOwnerSerializer(serializers.Serializer):
    """Minimal owner serializer for device representation - avoids circular recursion"""
    self = serializers.SerializerMethodField()
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    
    def get_self(self, obj):
        return f"/owners/{obj.id}"


class DeviceUserSerializer(serializers.Serializer):
    """Minimal user serializer for device representation - avoids circular recursion"""
    self = serializers.SerializerMethodField()
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    
    def get_self(self, obj):
        return f"/owners/{obj.id}"


class DeviceSerializer(serializers.ModelSerializer):
    """Device serializer matching specification format"""
    owner = DeviceOwnerSerializer(read_only=True)
    owner_id = serializers.IntegerField(write_only=True, required=False)
    group = GroupSerializer(read_only=True)
    group_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    location_lat = serializers.FloatField(write_only=True, required=False, allow_null=True)
    location_lon = serializers.FloatField(write_only=True, required=False, allow_null=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    users = DeviceUserSerializer(many=True, read_only=True)
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of user IDs to associate with device (maximum 6 users per Phase 0 spec)"
    )
    
    # Specification-compliant fields
    self = serializers.SerializerMethodField()
    propagate = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    owner_link = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = [
            'self', 'device_id', 'hid', 'name', 'location', 'latitude', 'longitude',
            'location_lat', 'location_lon', 'webhook_url', 'retry_limit',
            'owner', 'owner_id', 'owner_link', 'group', 'group_id', 'nid', 'active',
            'users', 'user_ids', 'propagate', 'position',
            'snumber', 'sname', 'city', 'province', 'city_code', 'country',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['device_id', 'created_at', 'updated_at']
    
    def get_self(self, obj):
        """Generate self link: /devices/{hid}"""
        request = self.context.get('request')
        if request:
            # Use HID for self link as per specification
            return f"/devices/{obj.hid}"
        return None
    
    def get_api_key_spec(self, obj):
        """Return api_key (will be serialized as 'api-key')"""
        return obj.api_key
    
    def get_propagate(self, obj):
        """Generate propagate object: {type: 'communal|radial|enhance', nid, radius}"""
        group = obj.group
        if not group:
            return None
        
        # Map group types to propagation types per specification
        if group.group_type in ['private', 'exclusive', 'data_logging']:
            # Communal: NID only
            return {
                'type': 'communal',
                'nid': obj.nid or group.nid,
                'radius': None
            }
        elif group.group_type == 'open':
            # Radial: radius only
            return {
                'type': 'radial',
                'nid': None,
                'radius': group.radius
            }
        elif group.group_type == 'enhanced':
            # Enhance: NID + radius
            return {
                'type': 'enhance',
                'nid': obj.nid or group.nid,
                'radius': group.radius
            }
        elif group.group_type == 'location':
            # Location: NID (0xFFFFFFFF for all) + radius (updated to 32-bit)
            return {
                'type': 'enhance',  # Location uses both NID and radius
                'nid': '0xFFFFFFFF',  # Special value for Location group (32-bit)
                'radius': group.radius
            }
        return None
    
    def get_position(self, obj):
        """Generate position object: {latitude, longitude}"""
        if obj.location:
            return {
                'latitude': obj.location.y,
                'longitude': obj.location.x
            }
        return None
    
    def get_owner_link(self, obj):
        """Generate owner self link: /owners/{owner_id}"""
        if obj.owner:
            return {
                'self': f"/owners/{obj.owner.id}"
            }
        return None
    
    def get_latitude(self, obj):
        if obj.location:
            return obj.location.y
        return None
    
    def get_longitude(self, obj):
        if obj.location:
            return obj.location.x
        return None
    
    def to_representation(self, instance):
        """Transform response to match specification format with hyphenated field names"""
        data = super().to_representation(instance)
        
        # Rename city_code to city-code
        if 'city_code' in data:
            data['city-code'] = data.pop('city_code')
        
        # Transform owner to specification format
        if 'owner' in data and data['owner']:
            owner_data = data['owner']
            # Add owner self link
            if 'id' in owner_data:
                owner_data['self'] = f"/owners/{owner_data['id']}"
        
        # Remove owner_link if owner is already included
        if 'owner_link' in data and 'owner' in data:
            data.pop('owner_link', None)
        elif 'owner_link' in data:
            data['owner'] = data.pop('owner_link')
        
        return data
    
    def validate_user_ids(self, value):
        """Validate that maximum 6 users are specified (Phase 0 spec requirement)"""
        if len(value) > Device.MAX_USERS:
            raise serializers.ValidationError(
                f'A device can have a maximum of {Device.MAX_USERS} users. '
                f'Received {len(value)} user IDs.'
            )
        # Remove duplicates
        unique_ids = list(set(value))
        
        # Ensure associated users are sub-users of the device owner
        from accounts.models import Owner
        if unique_ids:
            owner_id = self.initial_data.get('owner_id') if hasattr(self, 'initial_data') else None
            owner = None
            if owner_id:
                try:
                    owner = Owner.objects.get(id=owner_id)
                except Owner.DoesNotExist:
                    owner = None
            request = self.context.get('request')
            if not owner and request and request.user:
                owner = request.user
            
            if owner:
                allowed_ids = set(
                    Owner.objects.filter(parent_owner=owner).values_list('id', flat=True)
                )
                invalid_ids = [user_id for user_id in unique_ids if user_id not in allowed_ids]
                if invalid_ids:
                    raise serializers.ValidationError(
                        "Associated users must be sub-users of the device owner."
                    )
        
        return unique_ids
    
    def validate_group_id(self, value):
        """Validate that group exists and matches owner's group (per requirement #2)"""
        from messages.models import Group
        try:
            group = Group.objects.get(group_id=value)
        except Group.DoesNotExist:
            raise serializers.ValidationError(f"Group with ID {value} does not exist.")
        
        # Per requirement #2: Groups are assigned to owners, not devices
        # Device should use owner's group
        request = self.context.get('request')
        if request and request.user:
            owner = request.user
            if owner.group and owner.group.group_id != value:
                raise serializers.ValidationError(
                    f"Device group must match owner's group. Owner is assigned to '{owner.group.get_group_type_display}' group."
                )
        
        return value
    
    def validate_nid(self, value):
        """Validate NID format if provided - maximum is 0xFFFFFFFF (32-bit)"""
        if value is not None and value.strip() == '':
            return None
        
        if value:
            # Remove whitespace
            value = value.strip()
            
            # Remove hyphens if present (for readability)
            value_clean = value.replace('-', '')
            
            # Check if it's a hex string (starts with 0x)
            if value_clean.startswith('0x') or value_clean.startswith('0X'):
                try:
                    # Convert to integer to validate
                    nid_int = int(value_clean, 16)
                    # Maximum is 0xFFFFFFFF (32-bit, 4294967295 in decimal)
                    if nid_int > 0xFFFFFFFF:
                        raise serializers.ValidationError(
                            f"NID value {value} exceeds maximum allowed value of 4294967295 (0xFFFFFFFF)."
                        )
                    # Store as decimal format (user requirement)
                    return str(nid_int)
                except ValueError:
                    raise serializers.ValidationError(
                        f"Invalid NID format: {value}. Must be a valid hexadecimal number (e.g., 0x123456 or 0xFFFFFFFF) or decimal (e.g., 4294967295)."
                    )
            else:
                # Try to parse as decimal
                try:
                    nid_int = int(value_clean)
                    if nid_int < 0 or nid_int > 0xFFFFFFFF:
                        raise serializers.ValidationError(
                            f"NID value {value} must be between 0 and 4294967295 (0xFFFFFFFF)."
                        )
                    # Store as decimal format
                    return str(nid_int)
                except ValueError:
                    raise serializers.ValidationError(
                        f"Invalid NID format: {value}. Must be a valid number (hexadecimal with 0x prefix or decimal)."
                    )
        
        return value
    
    def create(self, validated_data):
        location_lat = validated_data.pop('location_lat', None)
        location_lon = validated_data.pop('location_lon', None)
        owner_id = validated_data.pop('owner_id', None)
        group_id = validated_data.pop('group_id', None)
        user_ids = validated_data.pop('user_ids', [])
        nid = validated_data.pop('nid', None)
        
        # Set owner from authenticated user if not provided
        if not owner_id:
            owner_id = self.context['request'].user.id
        
        from accounts.models import Owner
        from messages.models import Group
        
        try:
            owner = Owner.objects.get(id=owner_id)
        except Owner.DoesNotExist:
            raise serializers.ValidationError({'owner_id': f"Owner with ID {owner_id} does not exist."})
        
        # Per requirement #2: Groups are assigned to owners, not devices
        # Device should use owner's group, not a separate group_id
        owner_group = owner.group
        if not owner_group:
            raise serializers.ValidationError(
                {'group_id': "Owner must have a group assigned before registering devices. Please update your account settings."}
            )
        
        # Use owner's group instead of provided group_id
        group = owner_group
        
        # Verify group_id matches owner's group if provided
        if group_id and group_id != owner_group.group_id:
            raise serializers.ValidationError(
                {'group_id': f"Device group must match owner's group. Owner is assigned to '{owner_group.get_group_type_display}' group (ID: {owner_group.group_id})."}
            )
        
        # Check device limit based on owner's group (per requirement #2)
        device_count = owner.devices.filter(active=True).count()
        device_limit = owner.get_device_limit()
        
        if device_limit is not None and device_count >= device_limit:
            group_type_display = owner_group.get_group_type_display()
            raise serializers.ValidationError(
                f"Device limit reached. Owners in '{group_type_display}' group can only register {device_limit} device(s). "
                f"Current device count: {device_count}"
            )
        
        # Clean NID - set to None if empty string
        if nid and isinstance(nid, str) and nid.strip() == '':
            nid = None
        
        # Use owner's NID if device doesn't have one and owner has a group with NID
        if not nid and owner_group and owner_group.uses_nid():
            # Use owner's NID if available
            if owner.nid:
                nid = owner.nid
            elif owner_group.nid:
                nid = owner_group.nid
            else:
                # Generate a default NID in decimal format (32-bit max: 4294967295 = 0xFFFFFFFF)
                import secrets
                nid_int = secrets.randbelow(0xFFFFFFFF + 1)  # Random number 0 to 0xFFFFFFFF
                # Format as decimal (user requirement: decimal format for readability)
                nid = str(nid_int)
        
        # Assign Network ID based on group type (per specification)
        if not nid and group.uses_nid():
            # If group uses NID but device doesn't have one, use group's NID or generate one
            if group.nid:
                nid = group.nid
            else:
                # Generate a default NID for new devices in decimal format (32-bit max: 4294967295 = 0xFFFFFFFF)
                import secrets
                nid_int = secrets.randbelow(0xFFFFFFFF + 1)  # Random number 0 to 0xFFFFFFFF
                # Format as decimal (user requirement: decimal format for readability)
                nid = str(nid_int)
        
        # Build device creation kwargs
        device_kwargs = {
            'owner': owner,
            'group': group,
            **validated_data
        }
        
        # Only add nid if it's not None
        if nid is not None:
            device_kwargs['nid'] = nid
        
        device = Device.objects.create(**device_kwargs)
        
        # Set location if provided
        if location_lat is not None and location_lon is not None:
            try:
                device.set_location(location_lat, location_lon)
            except Exception as e:
                device.delete()  # Clean up if location fails
                raise serializers.ValidationError({'location': f"Invalid location: {str(e)}"})
        
        # Add users if provided
        if user_ids:
            try:
                users = Owner.objects.filter(id__in=user_ids)
                for user in users[:Device.MAX_USERS]:
                    try:
                        device.add_user(user)
                    except ValueError:
                        # Skip if max users reached (shouldn't happen due to validation, but handle gracefully)
                        break
            except Exception as e:
                # If user addition fails, delete the device and raise error
                device.delete()
                raise serializers.ValidationError({'user_ids': f"Error adding users: {str(e)}"})
        
        return device
    
    def update(self, instance, validated_data):
        location_lat = validated_data.pop('location_lat', None)
        location_lon = validated_data.pop('location_lon', None)
        group_id = validated_data.pop('group_id', None)
        user_ids = validated_data.pop('user_ids', None)
        nid = validated_data.pop('nid', None)
        
        if group_id:
            from messages.models import Group
            instance.group = Group.objects.get(group_id=group_id)
        
        # Update NID if group type requires it
        if nid is not None:
            instance.nid = nid
        elif instance.group and instance.group.uses_nid() and not instance.nid:
            # Assign NID if group uses it but device doesn't have one
            if instance.group.nid:
                instance.nid = instance.group.nid
        
        # Update location if provided
        if location_lat is not None and location_lon is not None:
            instance.set_location(location_lat, location_lon)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update users if user_ids provided
        if user_ids is not None:
            from accounts.models import Owner
            # Clear existing users and add new ones
            instance.users.clear()
            users = Owner.objects.filter(id__in=user_ids)
            for user in users[:Device.MAX_USERS]:
                try:
                    instance.add_user(user)
                except ValueError:
                    # Skip if max users reached
                    break
        
        return instance
