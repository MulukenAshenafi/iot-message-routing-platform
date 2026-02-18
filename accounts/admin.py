from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import Owner


@admin.register(Owner)
class OwnerAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'active', 'created_at']
    list_filter = ['active', 'is_staff', 'is_superuser', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('address', 'telephone', 'active')}),
    )
