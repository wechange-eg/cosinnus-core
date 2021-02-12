import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from oauth2_provider.decorators import protected_resource
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers.user import UserCreateSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('user', [])
    permission_classes = (permissions.IsAdminUser,)
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer

    def perform_create(self, serializer):
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.pop('password')
        # Overwrite username with ID
        user = serializer.save(username=email)
        user.username = user.id
        if password:
            user.set_password(password)
        user.save(update_fields=['username', 'password'])


class OAuthUserView(APIView):
    """
    Used by Oauth2 authentication (Rocket.Chat) to retrieve user details
    """

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ""
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            return Response({
                'success': True,
                'id': user.username if user.username.isdigit() else str(user.id),
                'email': user.email.lower(),
                'name': user.get_full_name(),
                'avatar': avatar_url,
            })
        else:
            return Response({
                'success': False,
            })


@protected_resource(scopes=['read'])
def oauth_user(request):
    return HttpResponse(json.dumps(
        {
            'id': request.resource_owner.id,
            'username': request.resource_owner.username,
            'email': request.resource_owner.email,
            'first_name': request.resource_owner.first_name,
            'last_name': request.resource_owner.last_name
        }
    ), content_type="application/json")


@protected_resource(scopes=['read'])
def oauth_profile(request):
    profile = request.resource_owner.cosinnus_profile
    media_tag_fields = ['visibility', 'location',
                        'location_lat', 'location_lon',
                        'place', 'valid_start', 'valid_end',
                        'approach']

    media_tag = profile.media_tag
    media_tag_dict = {}
    if media_tag:
        for field in media_tag_fields:
            media_tag_dict[field] = getattr(media_tag, field)

    return HttpResponse(json.dumps(
        {
            'avatar': profile.avatar_url,
            'description': profile.description,
            'website': profile.website,
            'language': profile.language,
            'media_tag': media_tag_dict
        }
    ), content_type="application/json")


@api_view(['GET'])
def current_user(request):
    """
    Determine the current user by their JWT token, and return their data
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


oauth_current_user = OAuthUserView.as_view()