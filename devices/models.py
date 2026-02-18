from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.db import models as django_models
from accounts.models import Owner
from messages.models import Group
import secrets
import hashlib


class Device(models.Model):
    """Device model with geographic location support"""
    MAX_USERS = 6  # Maximum number of users allowed per device (Phase 0 spec requirement)
    
    device_id = models.AutoField(primary_key=True)
    hid = models.CharField(max_length=100, unique=True, db_index=True, help_text="Hardware Identifier")
    name = models.CharField(max_length=200, blank=True, null=True, help_text="Device name")
    api_key = models.CharField(max_length=64, unique=True, db_index=True, editable=False)
    api_key_hash = models.CharField(max_length=128, help_text="Hashed API key")
    location = models.PointField(srid=4326, blank=True, null=True, help_text="Latitude, Longitude")
    webhook_url = models.URLField(blank=True, null=True)
    retry_limit = models.IntegerField(default=3)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='devices')
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name='devices')
    nid = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Network ID")
    active = models.BooleanField(default=True, db_index=True)
    # Address fields (specification requirement)
    snumber = models.CharField(max_length=20, blank=True, null=True, help_text="Street number")
    sname = models.CharField(max_length=200, blank=True, null=True, help_text="Street name")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="City")
    province = models.CharField(max_length=100, blank=True, null=True, help_text="Province/State")
    city_code = models.CharField(max_length=20, blank=True, null=True, help_text="Postal/ZIP code")
    country = models.CharField(max_length=100, blank=True, null=True, help_text="Country", default="Canada")
    users = models.ManyToManyField(
        Owner, 
        related_name='assigned_devices',
        blank=True,
        help_text="Users associated with this device (maximum 6 users per Phase 0 spec)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'devices'
        indexes = [
            django_models.Index(fields=['api_key']),
            django_models.Index(fields=['nid']),
            django_models.Index(fields=['active']),
        ]
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
    
    def __str__(self):
        return f"Device {self.hid} - {self.owner.email}"
    
    def clean(self):
        """Validate that device has maximum 6 users (Phase 0 spec requirement)"""
        from django.core.exceptions import ValidationError
        # Note: ManyToManyField validation needs to happen after save, so validation is in add_user() method
        # This clean() method is called before save, but ManyToMany fields are not available until after save
        pass
    
    def save(self, *args, **kwargs):
        # Generate API key if not set
        if not self.api_key:
            # Generate API key
            self.api_key = secrets.token_urlsafe(32)
            # Hash the API key for storage
            self.api_key_hash = hashlib.sha256(self.api_key.encode()).hexdigest()
        elif not self.api_key_hash:
            # If api_key exists but hash doesn't, create hash
            self.api_key_hash = hashlib.sha256(self.api_key.encode()).hexdigest()
        
        # Validate before saving
        self.full_clean()
        super().save(*args, **kwargs)
    
    def add_user(self, user):
        """Add a user to this device with validation for max 6 users"""
        if self.users.count() >= self.MAX_USERS:
            raise ValueError(f'A device can have a maximum of {self.MAX_USERS} users.')
        if not self.users.filter(pk=user.pk).exists():
            self.users.add(user)
    
    def get_user_ids(self):
        """Get list of user IDs associated with this device (max 6)"""
        return list(self.users.values_list('id', flat=True)[:self.MAX_USERS])
    
    def set_location(self, latitude, longitude):
        """Set device location from lat/lon"""
        self.location = Point(longitude, latitude, srid=4326)
        self.save()
    
    def verify_api_key(self, api_key):
        """Verify if provided API key matches stored hash"""
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key_hash == self.api_key_hash
