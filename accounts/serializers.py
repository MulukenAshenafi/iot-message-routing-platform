from rest_framework import serializers
from accounts.models import Owner


class OwnerSerializer(serializers.ModelSerializer):
    """Owner serializer matching specification format"""
    devices_count = serializers.SerializerMethodField()
    devices = serializers.SerializerMethodField()
    
    # Specification-compliant fields
    self = serializers.SerializerMethodField()
    tele = serializers.SerializerMethodField()  # telephone as 'tele'
    owner = serializers.SerializerMethodField()  # owner self reference
    
    group = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    nid = serializers.CharField(read_only=True)
    parent_owner_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Owner
        fields = [
            'self', 'id', 'username', 'email', 'first_name', 'last_name',
            'address', 'telephone', 'tele', 'active', 'expired',
            'devices_count', 'devices', 'owner', 'group', 'group_id', 'nid',
            'radius_km', 'parent_owner_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_group(self, obj):
        """Return group information if owner has a group"""
        if obj.group:
            from messages.serializers import GroupSerializer
            return GroupSerializer(obj.group).data
        return None
    
    def get_group_id(self, obj):
        """Return group ID if owner has a group"""
        return obj.group.group_id if obj.group else None
    
    def get_parent_owner_id(self, obj):
        """Return parent owner ID for sub-users"""
        return obj.parent_owner.id if obj.parent_owner else None
    
    def get_self(self, obj):
        """Generate self link: /owners/{id}"""
        return f"/owners/{obj.id}"
    
    def get_tele(self, obj):
        """Return telephone as 'tele'"""
        return obj.telephone
    
    def get_devices_count(self, obj):
        """Return count of devices"""
        return obj.devices.count()
    
    def get_devices(self, obj):
        """Return devices array - minimal representation to avoid circular recursion"""
        devices = obj.devices.all()[:50]  # Limit to prevent huge responses
        # Return minimal device data to avoid circular recursion with DeviceSerializer
        # which includes OwnerSerializer for owner/users
        result = []
        for device in devices:
            result.append({
                'self': f"/devices/{device.hid}",
                'device_id': device.device_id,
                'hid': device.hid,
                'name': device.name or '',
                'group_type': device.group.group_type if device.group else None,
                'nid': device.nid or '',
                'active': device.active,
                'created_at': device.created_at.isoformat() if device.created_at else None
            })
        return result
    
    def get_owner(self, obj):
        """Generate owner self reference: {self: '/owners/{id}'}"""
        return {
            'self': str(obj.id)  # Per specification, owner.self is just the ID as string
        }
    
    def to_representation(self, instance):
        """Transform response to match specification format with hyphenated field names"""
        data = super().to_representation(instance)
        
        # Remove telephone if tele is present
        if 'tele' in data and 'telephone' in data:
            data.pop('telephone', None)
        
        # Format expired date as string if present
        if 'expired' in data and data['expired']:
            # Format as "January 7, 2026" per specification example
            try:
                from datetime import datetime
                if isinstance(data['expired'], str):
                    # Already a string, try to parse and reformat
                    try:
                        dt = datetime.strptime(data['expired'], '%Y-%m-%d')
                        data['expired'] = dt.strftime("%B %d, %Y")
                    except:
                        pass
                elif hasattr(data['expired'], 'strftime'):
                    # It's a date object
                    data['expired'] = data['expired'].strftime("%B %d, %Y")
            except:
                pass
        
        return data


class OwnerCreateSerializer(serializers.ModelSerializer):
    """Owner creation serializer"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    group_id = serializers.IntegerField(write_only=True, required=False, allow_null=True, help_text="Group/Network ID to assign to owner")
    nid = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True, help_text="Network ID (NID) - leave empty to auto-generate")
    generate_nid = serializers.BooleanField(write_only=True, required=False, default=False, help_text="Auto-generate NID if not provided")
    radius_km = serializers.FloatField(write_only=True, required=False, allow_null=True, help_text="Routing radius in kilometers for distance-based groups")
    
    class Meta:
        model = Owner
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'address', 'telephone', 'password', 'password_confirm', 'expired',
            'group_id', 'nid', 'generate_nid', 'radius_km'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Validate NID if provided
        nid = attrs.get('nid', '').strip() if attrs.get('nid') else None
        if nid:
            # Remove hyphens if present (for readability)
            nid_clean = nid.replace('-', '')
            # Validate NID format (max 0xFFFFFFFF = 4294967295 in decimal)
            if nid_clean.startswith('0x') or nid_clean.startswith('0X'):
                try:
                    nid_int = int(nid_clean, 16)
                    if nid_int > 0xFFFFFFFF:
                        raise serializers.ValidationError(
                            {'nid': f"NID value {nid} exceeds maximum allowed value of 4294967295 (0xFFFFFFFF)."}
                        )
                except ValueError:
                    raise serializers.ValidationError(
                        {'nid': f"Invalid NID format: {nid}. Must be a valid hexadecimal number (e.g., 0x123456) or decimal (e.g., 4294967295)."}
                    )
            else:
                try:
                    nid_int = int(nid_clean)
                    if nid_int < 0 or nid_int > 0xFFFFFFFF:
                        raise serializers.ValidationError(
                            {'nid': f"NID value must be between 0 and 4294967295 (0xFFFFFFFF)."}
                        )
                except ValueError:
                    raise serializers.ValidationError(
                        {'nid': f"Invalid NID format: {nid}. Must be a valid number (hexadecimal with 0x prefix or decimal)."}
                    )
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        group_id = validated_data.pop('group_id', None)
        nid = validated_data.pop('nid', None)
        generate_nid = validated_data.pop('generate_nid', False)
        radius_km = validated_data.pop('radius_km', None)
        
        # Get group if provided
        group = None
        if group_id:
            from messages.models import Group
            try:
                group = Group.objects.get(group_id=group_id)
            except Group.DoesNotExist:
                raise serializers.ValidationError({'group_id': f"Group with ID {group_id} does not exist."})
        
        # Handle NID
        if not nid or (isinstance(nid, str) and nid.strip() == ''):
            if generate_nid or (group and group.uses_nid()):
                # Generate NID in decimal format (32-bit max: 4294967295 = 0xFFFFFFFF)
                import secrets
                nid_int = secrets.randbelow(0xFFFFFFFF + 1)  # Random number 0 to 0xFFFFFFFF
                # Format as decimal (user requirement: decimal format for readability)
                nid = str(nid_int)
            else:
                nid = None
        elif nid:
            # Format NID properly - accept both decimal and hex, but store as decimal
            nid = nid.strip()
            # Remove hyphens if present (for readability)
            nid_clean = nid.replace('-', '')
            if nid_clean.startswith('0x') or nid_clean.startswith('0X'):
                try:
                    nid_int = int(nid_clean, 16)
                    if nid_int < 0 or nid_int > 0xFFFFFFFF:
                        raise serializers.ValidationError(
                            {'nid': f"NID value must be between 0 and 4294967295 (0xFFFFFFFF)."}
                        )
                    # Convert to decimal format
                    nid = str(nid_int)
                except ValueError:
                    raise serializers.ValidationError(
                        {'nid': f"Invalid NID format: {nid}. Must be a valid number."}
                    )
            else:
                try:
                    nid_int = int(nid_clean)
                    if nid_int < 0 or nid_int > 0xFFFFFFFF:
                        raise serializers.ValidationError(
                            {'nid': f"NID value must be between 0 and 4294967295 (0xFFFFFFFF)."}
                        )
                    # Store as decimal
                    nid = str(nid_int)
                except ValueError:
                    raise serializers.ValidationError(
                        {'nid': f"Invalid NID format: {nid}. Must be a valid number."}
                    )
        
        # Create owner
        owner = Owner.objects.create(
            group=group,
            nid=nid,
            **validated_data
        )
        if radius_km is not None:
            owner.radius_km = radius_km
        owner.set_password(password)
        owner.save()  # This will trigger API key generation in save() method
        return owner


class SubUserCreateSerializer(serializers.ModelSerializer):
    """Create a sub-user under a parent owner"""
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    
    class Meta:
        model = Owner
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
    
    def create(self, validated_data):
        parent_owner = self.context.get('parent_owner')
        if not parent_owner:
            raise serializers.ValidationError("Parent owner is required.")
        
        user = Owner.objects.create_user(
            password=validated_data.pop('password'),
            **validated_data
        )
        user.parent_owner = parent_owner
        user.group = parent_owner.group
        user.save()
        return user
