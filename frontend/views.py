from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.db import models
from django.db.models import Q
from accounts.models import Owner
from devices.models import Device
from messages.models import DeviceInbox, Message
import requests
import json


def _build_internal_api_url(request, path: str) -> str:
    """Build internal API URL, preferring INTERNAL_API_BASE_URL when set."""
    base_url = getattr(settings, 'INTERNAL_API_BASE_URL', '')
    if base_url:
        return f"{base_url.rstrip('/')}{path}"
    return request.build_absolute_uri(path)


def login_view(request):
    """Login page view"""
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate - Owner model uses email as USERNAME_FIELD
        # So we need to check if input is email or username
        user = None
        
        # First try as email (since USERNAME_FIELD is email)
        if '@' in username_or_email:
            user = authenticate(request, username=username_or_email, password=password)
        else:
            # Try as username - need to get the user first, then authenticate with email
            try:
                from accounts.models import Owner
                owner = Owner.objects.get(username=username_or_email)
                user = authenticate(request, username=owner.email, password=password)
            except Owner.DoesNotExist:
                pass
        
        if user is not None:
            login(request, user)
            # Get JWT token from API
            # Since Owner model uses email as USERNAME_FIELD, JWT endpoint expects email
            try:
                api_url = _build_internal_api_url(request, '/api/auth/login/')
                # Try email first (since USERNAME_FIELD is email)
                response = requests.post(
                    api_url,
                    json={'username': user.email, 'password': password},
                    headers={'Content-Type': 'application/json'}
                )
                
                # If that fails, try with username
                if response.status_code != 200:
                    print(f"JWT login with email failed ({response.status_code}), trying username...")
                    response = requests.post(
                        api_url,
                        json={'username': user.username, 'password': password},
                        headers={'Content-Type': 'application/json'}
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    access_token = data.get('access')
                    refresh_token = data.get('refresh')
                    if access_token:
                        request.session['access_token'] = access_token
                        request.session['refresh_token'] = refresh_token
                        # Mark session as modified to ensure it's saved
                        request.session.modified = True
                        # Force session save
                        request.session.save()
                        print(f"✅ JWT token stored in session for user: {user.email} (token length: {len(access_token)})")
                        print(f"Session key: {request.session.session_key}")
                    else:
                        print(f"⚠️ Warning: No access token in JWT response: {data}")
                else:
                    error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
                    print(f"❌ JWT token fetch failed: {response.status_code} - {error_text}")
            except Exception as e:
                print(f"❌ JWT token fetch error: {e}")  # Continue even if JWT fetch fails
                import traceback
                traceback.print_exc()
            
            return redirect('frontend:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'frontend/login.html')


def register_view(request):
    """Registration page view"""
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')
    
    from messages.models import Group
    from messages.utils import ensure_default_groups
    ensure_default_groups()
    groups = Group.objects.all()
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'frontend/register.html')
        
        try:
            # Create user via API
            api_url = _build_internal_api_url(request, '/api/auth/register/')
            # Prepare registration data with sensible defaults
            # Extract first name from username or email if not provided
            first_name = request.POST.get('first_name', '').strip()
            if not first_name:
                # Try to extract from username (before any numbers or special chars)
                first_name = username.split('_')[0].split('-')[0].split('.')[0].title()
                if not first_name or len(first_name) < 2:
                    first_name = username.split('@')[0] if '@' in username else username
                    first_name = first_name.title()
            
            last_name = request.POST.get('last_name', '').strip()
            if not last_name:
                # Use a default last name
                last_name = 'User'
            
            registration_data = {
                'username': username,
                'email': email,
                'password': password1,
                'password_confirm': password2,
                'first_name': first_name,
                'last_name': last_name,
            }
            
            # Add group selection if provided
            group_id = request.POST.get('group_id')
            if group_id:
                registration_data['group_id'] = int(group_id)
            
            # Add routing radius if provided (distance-based groups)
            radius_km = request.POST.get('radius_km', '').strip()
            if radius_km:
                try:
                    registration_data['radius_km'] = float(radius_km)
                except ValueError:
                    messages.error(request, 'Routing radius must be a valid number.')
                    return render(request, 'frontend/register.html')
            
            response = requests.post(
                api_url,
                json=registration_data
            )
            
            if response.status_code == 201:
                data = response.json()
                # Authenticate and login
                user = authenticate(request, username=email, password=password1)  # Use email since USERNAME_FIELD is email
                if user:
                    login(request, user)
                    # Store tokens from registration response
                    tokens = data.get('tokens', {})
                    access_token = tokens.get('access')
                    refresh_token = tokens.get('refresh')
                    if access_token:
                        request.session['access_token'] = access_token
                        request.session['refresh_token'] = refresh_token
                        request.session.modified = True
                        request.session.save()
                        print(f"✅ JWT token stored in session for new user: {user.email} (token length: {len(access_token)})")
                    messages.success(request, 'Account created successfully!')
                    return redirect('frontend:dashboard')
                else:
                    messages.error(request, 'Account created but login failed. Please try logging in.')
            else:
                error_data = response.json()
                # Handle validation errors
                if isinstance(error_data, dict):
                    error_messages = []
                    for field, errors in error_data.items():
                        if isinstance(errors, list):
                            error_messages.extend([f"{field}: {error}" for error in errors])
                        else:
                            error_messages.append(f"{field}: {errors}")
                    messages.error(request, ' '.join(error_messages) if error_messages else 'Registration failed.')
                else:
                    messages.error(request, error_data.get('error', 'Registration failed.'))
        except requests.exceptions.RequestException as e:
            messages.error(request, f'Connection error: {str(e)}')
        except Exception as e:
            messages.error(request, f'Registration error: {str(e)}')
    
    context = {
        'groups': groups,
    }
    return render(request, 'frontend/register.html', context)


@login_required
def logout_view(request):
    """Logout view"""
    from django.contrib.auth import logout
    logout(request)
    request.session.flush()
    return redirect('frontend:login')


@login_required
def dashboard_view(request):
    """Dashboard page view - redirects admins to admin dashboard"""
    # Redirect admins to custom admin dashboard
    if request.user.is_staff:
        return redirect('frontend:admin_dashboard')  # Redirects to /admin-dashboard/
    
    # Regular user dashboard
    devices = Device.objects.filter(owner=request.user, active=True)
    system_events_count = Message.objects.filter(source_device__owner=request.user).count()
    active_devices_count = devices.count()
    
    # Get JWT token from session if available, or generate new one
    access_token = request.session.get('access_token', '')
    if not access_token and request.user.is_authenticated:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session['refresh_token'] = str(refresh)
            request.session.modified = True
            request.session.save()
            print(f"✅ Generated new JWT token for dashboard user: {request.user.email}")
        except Exception as e:
            print(f"⚠️ Could not generate JWT token for dashboard: {e}")
    
    context = {
        'devices': devices[:10],  # Limit to 10 for display
        'active_devices_count': active_devices_count,
        'system_events_count': system_events_count,
        'is_admin': False,
        'access_token': access_token,
    }
    
    return render(request, 'frontend/dashboard.html', context)


@login_required
def admin_dashboard_view(request):
    """Custom Admin Dashboard - comprehensive admin functionality"""
    # Only allow staff users
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from accounts.models import Owner
    from messages.models import Group, Message, DeviceInbox
    
    # System Statistics
    total_users = Owner.objects.count()
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(active=True).count()
    total_messages = Message.objects.count()
    total_groups = Group.objects.count()
    pending_inbox_messages = DeviceInbox.objects.filter(status='pending').count()
    
    # Recent Activity
    recent_devices = Device.objects.select_related('owner', 'group').order_by('-created_at')[:10]
    recent_users = Owner.objects.order_by('-date_joined')[:10]
    recent_messages = Message.objects.select_related('source_device', 'source_device__owner').order_by('-timestamp')[:20]
    
    # Group Statistics
    group_stats = []
    for group in Group.objects.all():
        device_count = Device.objects.filter(group=group, active=True).count()
        owner_count = Owner.objects.filter(group=group).count()
        group_stats.append({
            'group': group,
            'device_count': device_count,
            'owner_count': owner_count,
        })
    
    # User Statistics
    admin_users = Owner.objects.filter(is_staff=True).count()
    regular_users = Owner.objects.filter(is_staff=False).count()
    users_with_devices = Owner.objects.filter(devices__isnull=False).distinct().count()
    users_without_devices = total_users - users_with_devices
    
    # Device Statistics by Group
    device_by_group = {}
    for group in Group.objects.all():
        device_by_group[group.get_group_type_display()] = Device.objects.filter(group=group, active=True).count()
    
    # Get JWT token from session if available, or generate new one
    access_token = request.session.get('access_token', '')
    if not access_token and request.user.is_authenticated:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session['refresh_token'] = str(refresh)
            request.session.modified = True
            request.session.save()
        except Exception as e:
            print(f"⚠️ Could not generate JWT token for admin dashboard: {e}")
    
    context = {
        'total_users': total_users,
        'total_devices': total_devices,
        'active_devices': active_devices,
        'total_messages': total_messages,
        'total_groups': total_groups,
        'pending_inbox_messages': pending_inbox_messages,
        'recent_devices': recent_devices,
        'recent_users': recent_users,
        'recent_messages': recent_messages,
        'group_stats': group_stats,
        'admin_users': admin_users,
        'regular_users': regular_users,
        'users_with_devices': users_with_devices,
        'users_without_devices': users_without_devices,
        'device_by_group': device_by_group,
        'is_admin': True,
        'access_token': access_token,
    }
    
    return render(request, 'frontend/admin_dashboard.html', context)


@login_required
def studio_view(request):
    """Message Studio page view"""
    # Admin can see all devices, regular users only their own + assigned devices
    if request.user.is_staff:
        devices = Device.objects.filter(active=True).prefetch_related('users', 'group', 'owner')
    else:
        # User's own devices + devices where user is in users list
        from django.db import models
        devices = Device.objects.filter(
            models.Q(owner=request.user) | models.Q(users=request.user),
            active=True
        ).prefetch_related('users', 'group').distinct()
    
    # Get JWT token from session if available
    access_token = request.session.get('access_token', '')
    
    # If token is missing but user is authenticated, try to get a new one
    if not access_token and request.user.is_authenticated:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            # Generate new token for the user
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            # Store in session
            request.session['access_token'] = access_token
            request.session['refresh_token'] = str(refresh)
            request.session.modified = True
            request.session.save()
            print(f"✅ Generated new JWT token for user: {request.user.email}")
        except Exception as e:
            print(f"⚠️ Could not generate JWT token: {e}")
            # Fallback: try to get token via API
            try:
                api_url = _build_internal_api_url(request, '/api/auth/login/')
                # Try with email first (since USERNAME_FIELD is email)
                response = requests.post(
                    api_url,
                    json={'username': request.user.email, 'password': ''},  # We can't get password here
                    headers={'Content-Type': 'application/json'}
                )
                # This won't work without password, so we'll rely on RefreshToken above
            except:
                pass
    
    # Note: We don't expose API keys in the template for security
    # API keys should be fetched via API when needed
    
    context = {
        'devices': devices,
        'is_admin': request.user.is_staff,
        'access_token': access_token,
    }
    
    print(f"Studio view - access_token in context: {'Yes' if access_token else 'No'} (length: {len(access_token) if access_token else 0})")
    
    return render(request, 'frontend/studio.html', context)


@login_required
def inbox_view(request):
    """Inbox page view"""
    # Admin can see all devices, regular users only their own + assigned devices
    if request.user.is_staff:
        devices = Device.objects.filter(active=True).prefetch_related('users', 'group', 'owner')
    else:
        # User's own devices + devices where user is in users list
        from django.db import models
        devices = Device.objects.filter(
            models.Q(owner=request.user) | models.Q(users=request.user),
            active=True
        ).prefetch_related('users', 'group').distinct()
    
    # Get JWT token from session if available, or generate new one
    access_token = request.session.get('access_token', '')
    if not access_token and request.user.is_authenticated:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session['refresh_token'] = str(refresh)
            request.session.modified = True
            request.session.save()
            print(f"✅ Generated new JWT token for inbox user: {request.user.email}")
        except Exception as e:
            print(f"⚠️ Could not generate JWT token for inbox: {e}")
    
    context = {
        'devices': devices,
        'is_admin': request.user.is_staff,
        'access_token': access_token,
    }
    
    return render(request, 'frontend/inbox.html', context)


@login_required
def register_device_view(request):
    """Device registration page view - Now uses API for consistency"""
    from messages.models import Group
    
    if getattr(request.user, 'parent_owner', None):
        messages.error(request, 'Sub-users cannot register devices. Please contact the account owner.')
        return redirect('frontend:dashboard')
    
    # Check if user has a group assigned
    if not request.user.group:
        messages.error(request, 'You must have a group assigned to your account before registering devices. Please contact an administrator.')
        return redirect('frontend:dashboard')
    
    # Get JWT token from session if available, or generate new one
    access_token = request.session.get('access_token', '')
    if not access_token and request.user.is_authenticated:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session['refresh_token'] = str(refresh)
            request.session.modified = True
            request.session.save()
        except Exception as e:
            print(f"⚠️ Could not generate JWT token for register device: {e}")
    
    groups = Group.objects.all()
    context = {
        'groups': groups,
        'access_token': access_token,
        'user': request.user,  # Pass user to template
    }
    
    return render(request, 'frontend/register_device.html', context)


@login_required
def device_detail_view(request, device_id):
    """Device detail page view - does not expose sensitive data"""
    try:
        device = Device.objects.get(device_id=device_id, active=True)
        
        # Check permission
        if not (request.user == device.owner or request.user.is_staff):
            messages.error(request, 'Permission denied')
            return redirect('frontend:dashboard')
        
        # Get device messages
        from messages.models import Message, DeviceInbox
        messages_list = Message.objects.filter(source_device=device).order_by('-timestamp')[:20]
        inbox_messages = DeviceInbox.objects.filter(device=device, status='pending').select_related('message')[:10]
        
        # Get associated users (prefetch for template display)
        device.users.all()  # Trigger prefetch
        
        # Get JWT token from session if available, or generate new one
        access_token = request.session.get('access_token', '')
        if not access_token and request.user.is_authenticated:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(request.user)
                access_token = str(refresh.access_token)
                request.session['access_token'] = access_token
                request.session['refresh_token'] = str(refresh)
                request.session.modified = True
                request.session.save()
                print(f"✅ Generated new JWT token for device detail user: {request.user.email}")
            except Exception as e:
                print(f"⚠️ Could not generate JWT token for device detail: {e}")
        
        # Prefetch users for template display
        device_users = list(device.users.all())
        
        # Don't expose API key directly - will be fetched via API if needed
        # Only expose safe device information
        context = {
            'device': device,
            'device_users': device_users,  # For template display
            'messages': messages_list,
            'inbox_messages': inbox_messages,
            'device_id': device.device_id,  # For API calls
            'access_token': access_token,
        }
        
        return render(request, 'frontend/device_detail.html', context)
    except Device.DoesNotExist:
        messages.error(request, 'Device not found')
        return redirect('frontend:dashboard')


@login_required
def admin_users_view(request):
    """Admin Users Management Page"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from accounts.models import Owner
    from django.db.models import Count
    
    # Get all users with device counts
    users = Owner.objects.annotate(
        device_count=Count('devices')
    ).select_related('group').order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Get JWT token
    access_token = request.session.get('access_token', '')
    if not access_token:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session.modified = True
        except:
            pass
    
    context = {
        'users': users,
        'search_query': search_query,
        'access_token': access_token,
    }
    return render(request, 'frontend/admin_users.html', context)


@login_required
def admin_devices_view(request):
    """Admin Devices Management Page"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    devices = Device.objects.select_related('owner', 'group').prefetch_related('users').order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        devices = devices.filter(
            Q(hid__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(owner__email__icontains=search_query) |
            Q(owner__username__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        devices = devices.filter(active=True)
    elif status_filter == 'inactive':
        devices = devices.filter(active=False)
    
    # Get JWT token
    access_token = request.session.get('access_token', '')
    if not access_token:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session.modified = True
        except:
            pass
    
    context = {
        'devices': devices,
        'search_query': search_query,
        'status_filter': status_filter,
        'access_token': access_token,
    }
    return render(request, 'frontend/admin_devices.html', context)


@login_required
def admin_messages_view(request):
    """Admin Messages Management Page"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from messages.models import Message, DeviceInbox
    
    messages_list = Message.objects.select_related(
        'source_device', 'source_device__owner'
    ).order_by('-timestamp')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        messages_list = messages_list.filter(
            Q(source_device__hid__icontains=search_query) |
            Q(source_device__owner__email__icontains=search_query) |
            Q(type__icontains=search_query)
        )
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter in ['alert', 'alarm']:
        messages_list = messages_list.filter(type=type_filter)
    
    # Get inbox statistics
    inbox_stats = {
        'pending': DeviceInbox.objects.filter(status='pending').count(),
        'acknowledged': DeviceInbox.objects.filter(status='acknowledged').count(),
        'delivered': DeviceInbox.objects.filter(status='delivered').count(),
    }
    
    # Get JWT token
    access_token = request.session.get('access_token', '')
    if not access_token:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session.modified = True
        except:
            pass
    
    context = {
        'messages': messages_list[:100],  # Limit to 100 for performance
        'search_query': search_query,
        'type_filter': type_filter,
        'inbox_stats': inbox_stats,
        'access_token': access_token,
    }
    return render(request, 'frontend/admin_messages.html', context)


@login_required
def admin_groups_view(request):
    """Admin Groups Management Page"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from messages.models import Group
    from messages.utils import ensure_default_groups
    from django.db.models import Count, Q
    
    ensure_default_groups()
    groups = Group.objects.annotate(
        device_count=Count('devices', filter=Q(devices__active=True)),
        owner_count=Count('owners')
    ).order_by('group_type')
    
    # Get JWT token
    access_token = request.session.get('access_token', '')
    if not access_token:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session.modified = True
        except:
            pass
    
    context = {
        'groups': groups,
        'access_token': access_token,
    }
    return render(request, 'frontend/admin_groups.html', context)


@login_required
def admin_user_create_view(request):
    """Admin: Create new user"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from messages.models import Group
    from messages.utils import ensure_default_groups
    
    ensure_default_groups()
    
    if request.method == 'POST':
        try:
            from accounts.models import Owner
            import secrets
            
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            group_id = request.POST.get('group_id')
            nid = request.POST.get('nid', '')
            radius_km = request.POST.get('radius_km', '').strip()
            generate_nid = request.POST.get('generate_nid') == 'on'
            is_staff = request.POST.get('is_staff') == 'on'
            
            if not username or not email or not password:
                messages.error(request, 'Username, email, and password are required.')
                return redirect('frontend:admin_user_create')
            
            # Create user
            user = Owner.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff,
            )
            
            # Assign group
            if group_id:
                group = Group.objects.get(group_id=group_id)
                user.group = group
                
                # Handle NID
                if generate_nid or (group.uses_nid() and not nid):
                    user.nid = secrets.token_hex(8)
                elif nid:
                    user.nid = nid
                
                if radius_km:
                    try:
                        user.radius_km = float(radius_km)
                    except ValueError:
                        messages.error(request, 'Routing radius must be a valid number.')
                        return redirect('frontend:admin_user_create')
                
                user.save()
            
            messages.success(request, f'User {username} created successfully!')
            return redirect('frontend:admin_users')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    groups = Group.objects.all()
    context = {'groups': groups}
    return render(request, 'frontend/admin_user_form.html', context)


@login_required
def admin_user_edit_view(request, user_id):
    """Admin: Edit user"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from accounts.models import Owner
    from messages.models import Group
    from messages.utils import ensure_default_groups
    
    ensure_default_groups()
    
    try:
        user = Owner.objects.get(id=user_id)
    except Owner.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('frontend:admin_users')
    
    if request.method == 'POST':
        try:
            user.username = request.POST.get('username', user.username)
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.active = request.POST.get('active') != 'off'
            
            # Update password if provided
            password = request.POST.get('password')
            if password:
                user.set_password(password)
            
            # Update group
            group_id = request.POST.get('group_id')
            if group_id:
                group = Group.objects.get(group_id=group_id)
                user.group = group
                
                # Update NID
                nid = request.POST.get('nid', '')
                if nid:
                    user.nid = nid
                
                radius_km = request.POST.get('radius_km', '').strip()
                if radius_km:
                    try:
                        user.radius_km = float(radius_km)
                    except ValueError:
                        messages.error(request, 'Routing radius must be a valid number.')
                        return redirect('frontend:admin_user_edit', user_id=user.id)
            
            user.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('frontend:admin_users')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    groups = Group.objects.all()
    context = {'edit_user': user, 'groups': groups}
    return render(request, 'frontend/admin_user_form.html', context)


@login_required
def admin_user_delete_view(request, user_id):
    """Admin: Delete user"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from accounts.models import Owner
    
    if request.method == 'POST':
        try:
            user = Owner.objects.get(id=user_id)
            if user == request.user:
                messages.error(request, 'You cannot delete your own account.')
                return redirect('frontend:admin_users')
            username = user.username
            user.delete()
            messages.success(request, f'User {username} deleted successfully!')
        except Owner.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    
    return redirect('frontend:admin_users')


@login_required
def admin_device_create_view(request):
    """Admin: Create new device"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from messages.models import Group
    from accounts.models import Owner
    from messages.utils import ensure_default_groups
    
    ensure_default_groups()
    
    if request.method == 'POST':
        try:
            hid = request.POST.get('hid')
            name = request.POST.get('name', '')
            owner_id = request.POST.get('owner_id')
            group_id = request.POST.get('group_id')
            nid = request.POST.get('nid', '')
            active = request.POST.get('active') != 'off'
            
            if not hid or not owner_id:
                messages.error(request, 'HID and Owner are required.')
                return redirect('frontend:admin_device_create')
            
            owner = Owner.objects.get(id=owner_id)
            
            # Check device limit
            if owner.get_device_limit() == 1 and owner.devices.count() >= 1:
                messages.error(request, f'Owner {owner.email} has reached the device limit for their group.')
                return redirect('frontend:admin_device_create')
            
            # Resolve group (required for Device model)
            group = None
            if group_id:
                group = Group.objects.get(group_id=group_id)
            else:
                group = owner.group
            
            if not group:
                messages.error(request, 'Owner must have a group or select a group for the device.')
                return redirect('frontend:admin_device_create')
            
            # Handle NID
            if group.uses_nid() and not nid:
                nid = owner.nid or group.nid
            
            device = Device.objects.create(
                hid=hid,
                name=name,
                owner=owner,
                group=group,
                nid=nid or None,
                active=active,
            )
            
            messages.success(request, f'Device {hid} created successfully!')
            return redirect('frontend:admin_devices')
        except Exception as e:
            messages.error(request, f'Error creating device: {str(e)}')
    
    groups = Group.objects.all()
    owners = Owner.objects.all().select_related('group')
    context = {'groups': groups, 'owners': owners}
    return render(request, 'frontend/admin_device_form.html', context)


@login_required
def admin_device_edit_view(request, device_id):
    """Admin: Edit device"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from messages.models import Group
    from accounts.models import Owner
    from messages.utils import ensure_default_groups
    
    ensure_default_groups()
    
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        messages.error(request, 'Device not found.')
        return redirect('frontend:admin_devices')
    
    if request.method == 'POST':
        try:
            device.hid = request.POST.get('hid', device.hid)
            device.name = request.POST.get('name', '')
            device.active = request.POST.get('active') != 'off'
            
            # Update owner
            owner_id = request.POST.get('owner_id')
            if owner_id:
                owner = Owner.objects.get(id=owner_id)
                device.owner = owner
            
            # Update group
            group_id = request.POST.get('group_id')
            if group_id:
                group = Group.objects.get(group_id=group_id)
                device.group = group
                
                # Update NID
                nid = request.POST.get('nid', '')
                if nid:
                    device.nid = nid
            
            device.save()
            messages.success(request, f'Device {device.hid} updated successfully!')
            return redirect('frontend:admin_devices')
        except Exception as e:
            messages.error(request, f'Error updating device: {str(e)}')
    
    groups = Group.objects.all()
    owners = Owner.objects.all().select_related('group')
    context = {'device': device, 'groups': groups, 'owners': owners}
    return render(request, 'frontend/admin_device_form.html', context)


@login_required
def admin_device_delete_view(request, device_id):
    """Admin: Delete device"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    if request.method == 'POST':
        try:
            device = Device.objects.get(device_id=device_id)
            hid = device.hid
            device.delete()
            messages.success(request, f'Device {hid} deleted successfully!')
        except Device.DoesNotExist:
            messages.error(request, 'Device not found.')
        except Exception as e:
            messages.error(request, f'Error deleting device: {str(e)}')
    
    return redirect('frontend:admin_devices')


@login_required
def admin_message_delete_view(request, message_id):
    """Admin: Delete message"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('frontend:dashboard')
    
    from messages.models import Message
    
    if request.method == 'POST':
        try:
            message = Message.objects.get(message_id=message_id)
            message.delete()
            messages.success(request, 'Message deleted successfully!')
        except Message.DoesNotExist:
            messages.error(request, 'Message not found.')
        except Exception as e:
            messages.error(request, f'Error deleting message: {str(e)}')
    
    return redirect('frontend:admin_messages')


@login_required
def user_device_edit_view(request, device_id):
    """User: Edit own device"""
    try:
        device = Device.objects.get(device_id=device_id, active=True)
        
        # Check permission - user must be owner
        if device.owner != request.user and not request.user.is_staff:
            messages.error(request, 'Permission denied')
            return redirect('frontend:dashboard')
        
        if request.method == 'POST':
            try:
                device.name = request.POST.get('name', device.name)
                device.webhook_url = request.POST.get('webhook_url', '')
                device.retry_limit = int(request.POST.get('retry_limit', device.retry_limit or 3))
                
                user_ids_raw = request.POST.get('user_ids', '').strip()
                if user_ids_raw:
                    user_ids = [int(uid) for uid in user_ids_raw.split(',') if uid.strip().isdigit()]
                    if len(user_ids) > Device.MAX_USERS:
                        messages.error(request, f'A device can have a maximum of {Device.MAX_USERS} users.')
                        return redirect('frontend:user_device_edit', device_id=device.device_id)
                    # Only allow sub-users of the device owner
                    valid_users = device.owner.sub_users.filter(id__in=user_ids)
                    device.users.set(valid_users)
                else:
                    device.users.clear()
                
                device.save()
                messages.success(request, f'Device {device.hid} updated successfully!')
                return redirect('frontend:device_detail', device_id=device.device_id)
            except Exception as e:
                messages.error(request, f'Error updating device: {str(e)}')
        
        context = {
            'device': device,
            'device_user_ids': list(device.users.values_list('id', flat=True))
        }
        return render(request, 'frontend/user_device_form.html', context)
    except Device.DoesNotExist:
        messages.error(request, 'Device not found')
        return redirect('frontend:dashboard')


@login_required
def user_device_delete_view(request, device_id):
    """User: Delete own device"""
    if request.method == 'POST':
        try:
            device = Device.objects.get(device_id=device_id, active=True)
            
            # Check permission - user must be owner
            if device.owner != request.user and not request.user.is_staff:
                messages.error(request, 'Permission denied')
                return redirect('frontend:dashboard')
            
            hid = device.hid
            device.delete()
            messages.success(request, f'Device {hid} deleted successfully!')
        except Device.DoesNotExist:
            messages.error(request, 'Device not found.')
        except Exception as e:
            messages.error(request, f'Error deleting device: {str(e)}')
    
    return redirect('frontend:dashboard')


@login_required
def user_message_delete_view(request, message_id):
    """User: Delete own message"""
    from messages.models import Message
    
    if request.method == 'POST':
        try:
            message = Message.objects.get(message_id=message_id)
            
            # Check permission - user must be device owner
            if message.source_device.owner != request.user and not request.user.is_staff:
                messages.error(request, 'Permission denied')
                return redirect('frontend:dashboard')
            
            message.delete()
            messages.success(request, 'Message deleted successfully!')
        except Message.DoesNotExist:
            messages.error(request, 'Message not found.')
        except Exception as e:
            messages.error(request, f'Error deleting message: {str(e)}')
    
    return redirect('frontend:inbox')


@login_required
def settings_view(request):
    """Settings page view"""
    if request.method == 'POST':
        # Handle settings updates
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        address = request.POST.get('address', '')
        telephone = request.POST.get('telephone', '')
        
        try:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.address = address
            request.user.telephone = telephone
            request.user.save()
            messages.success(request, 'Settings updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    # Get JWT token from session if available, or generate new one
    access_token = request.session.get('access_token', '')
    if not access_token and request.user.is_authenticated:
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(request.user)
            access_token = str(refresh.access_token)
            request.session['access_token'] = access_token
            request.session['refresh_token'] = str(refresh)
            request.session.modified = True
            request.session.save()
            print(f"✅ Generated new JWT token for settings user: {request.user.email}")
        except Exception as e:
            print(f"⚠️ Could not generate JWT token for settings: {e}")
    
    context = {
        'user': request.user,
        'access_token': access_token,
    }
    
    return render(request, 'frontend/settings.html', context)
