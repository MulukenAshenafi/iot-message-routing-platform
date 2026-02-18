from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import Owner
from accounts.serializers import OwnerSerializer, OwnerCreateSerializer, SubUserCreateSerializer
from devices.serializers import DeviceSerializer


class OwnerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Owner management
    """
    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OwnerCreateSerializer
        return OwnerSerializer
    
    def get_permissions(self):
        """
        Allow registration without authentication
        """
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=True, methods=['get'])
    def devices(self, request, pk=None):
        """
        Get all devices belonging to a specific owner
        GET /api/owners/{id}/devices/
        """
        owner = self.get_object()
        devices = owner.devices.all()
        serializer = DeviceSerializer(devices, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile
        GET /api/owners/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get', 'post'], url_path='sub-users')
    def sub_users(self, request):
        """
        Get or create sub-users for the current owner
        GET /api/owners/sub-users/
        POST /api/owners/sub-users/
        """
        if request.user.parent_owner:
            return Response({'error': 'Sub-users cannot manage other users.'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.method == 'POST':
            serializer = SubUserCreateSerializer(data=request.data, context={'parent_owner': request.user})
            if serializer.is_valid():
                user = serializer.save()
                return Response(OwnerSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        users = request.user.sub_users.all()
        serializer = OwnerSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='email/(?P<email>[^/]+)')
    def owner_by_email(self, request, email=None):
        """
        Get owner by email
        GET /api/owners/email/{email}/
        """
        from urllib.parse import unquote
        # Decode URL-encoded email
        email = unquote(email)
        
        try:
            owner = Owner.objects.get(email=email, active=True)
            
            # Check permission
            if not (request.user == owner or request.user.is_staff):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = OwnerSerializer(owner, context={'request': request})
            return Response(serializer.data)
        except Owner.DoesNotExist:
            return Response(
                {'error': 'Owner not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    User registration endpoint that returns JWT token
    POST /api/auth/register/
    """
    serializer = OwnerCreateSerializer(data=request.data)
    if serializer.is_valid():
        owner = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(owner)
        
        user_data = OwnerSerializer(owner, context={'request': request}).data
        # Include API key only at creation time
        user_data['api-key'] = owner.api_key
        
        return Response({
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    User logout endpoint - blacklists refresh token
    POST /api/auth/logout/
    Body: {"refresh_token": "..."}
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            # Try to blacklist if blacklist app is installed
            try:
                token.blacklist()
            except AttributeError:
                # Blacklist app not installed, just validate token
                pass
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'refresh_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            {'error': f'Invalid token: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
