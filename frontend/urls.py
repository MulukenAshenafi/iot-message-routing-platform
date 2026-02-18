from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('studio/', views.studio_view, name='studio'),
    path('inbox/', views.inbox_view, name='inbox'),
    path('settings/', views.settings_view, name='settings'),
    path('devices/register/', views.register_device_view, name='register_device'),
    path('devices/<int:device_id>/', views.device_detail_view, name='device_detail'),
    # Admin routes
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/users/create/', views.admin_user_create_view, name='admin_user_create'),
    path('admin/users/<int:user_id>/edit/', views.admin_user_edit_view, name='admin_user_edit'),
    path('admin/users/<int:user_id>/delete/', views.admin_user_delete_view, name='admin_user_delete'),
    path('admin/devices/', views.admin_devices_view, name='admin_devices'),
    path('admin/devices/create/', views.admin_device_create_view, name='admin_device_create'),
    path('admin/devices/<int:device_id>/edit/', views.admin_device_edit_view, name='admin_device_edit'),
    path('admin/devices/<int:device_id>/delete/', views.admin_device_delete_view, name='admin_device_delete'),
    path('admin/messages/', views.admin_messages_view, name='admin_messages'),
    path('admin/messages/<int:message_id>/delete/', views.admin_message_delete_view, name='admin_message_delete'),
    path('admin/groups/', views.admin_groups_view, name='admin_groups'),
    # User management routes
    path('devices/<int:device_id>/edit/', views.user_device_edit_view, name='user_device_edit'),
    path('devices/<int:device_id>/delete/', views.user_device_delete_view, name='user_device_delete'),
    path('messages/<int:message_id>/delete/', views.user_message_delete_view, name='user_message_delete'),
    path('', views.dashboard_view, name='dashboard'),  # Must be last to catch root
]

