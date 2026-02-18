from django.contrib.auth.models import AbstractUser
from django.db import models


class Owner(AbstractUser):
    """Owner/User model with extended fields"""
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True, default='')
    last_name = models.CharField(max_length=100, blank=True, default='')
    address = models.TextField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True, help_text="Telephone number (also accessible as 'tele')")
    active = models.BooleanField(default=True)
    expired = models.DateField(blank=True, null=True, help_text="Account expiration date")
    api_key = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True, editable=False, help_text="Owner API key")
    api_key_hash = models.CharField(max_length=128, blank=True, null=True, help_text="Hashed API key")
    # Group assignment at owner level (per requirement)
    # Note: messages app uses label 'iot_messages' to avoid conflict with django.contrib.messages
    group = models.ForeignKey('iot_messages.Group', on_delete=models.PROTECT, blank=True, null=True, related_name='owners', help_text="Group/Network assigned to owner")
    # Owner-level NID (can be generated or manually entered)
    nid = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Network ID (NID) - can be auto-generated or manually entered (max 0xFFFFFFFF)")
    radius_km = models.FloatField(blank=True, null=True, help_text="Routing radius in kilometers for distance-based groups")
    parent_owner = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_users',
        help_text="Parent owner for sub-user accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # first_name and last_name are now optional
    
    class Meta:
        db_table = 'owners'
        verbose_name = 'Owner'
        verbose_name_plural = 'Owners'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def save(self, *args, **kwargs):
        """Generate API key for owner if not set"""
        import secrets
        import hashlib
        # Generate API key if not set
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
        # Hash the API key for storage
        if self.api_key and not self.api_key_hash:
            self.api_key_hash = hashlib.sha256(self.api_key.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    def can_register_multiple_devices(self):
        """Check if owner can register multiple devices based on group type"""
        if not self.group:
            return False
        # Private and Data Logger owners can have multiple devices
        return self.group.group_type in ['private', 'data_logging']
    
    def get_device_limit(self):
        """Get the maximum number of devices this owner can register"""
        if not self.group:
            return 0
        if self.can_register_multiple_devices():
            return None  # No limit
        return 1  # Only one device for Exclusive, Open, Enhance, Location
