import json

import random

from django.contrib.auth import get_user_model, authenticate, login
from django.http import HttpResponse
from oauth2_provider.decorators import protected_resource
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers, authentication

from cosinnus.conf import settings
from ..serializers.user import UserCreateUpdateSerializer, UserSerializer
from ...models import get_user_profile_model, CosinnusGroup, CosinnusGroupMembership, MEMBERSHIP_MEMBER
from cosinnus.models.membership import MEMBER_STATUS, MEMBERSHIP_MANAGER,\
    MEMBERSHIP_ADMIN
from cosinnus.api.views.mixins import CosinnusFilterQuerySetMixin
from cosinnus.views.common import LoginViewAdditionalLogicMixin

User = get_user_model()


class UserViewSet(CosinnusFilterQuerySetMixin, viewsets.ModelViewSet):
    http_method_names = getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('user', [])
    permission_classes = (permissions.IsAdminUser,)
    queryset = User.objects.all()
    serializer_class = UserCreateUpdateSerializer
    
    FILTER_DEFAULT_ORDER = ['-date_joined', ]

    def perform_create(self, serializer):
        self.create_or_update(serializer)

    def perform_update(self, serializer):
        self.create_or_update(serializer)

    def create_or_update(self, serializer):
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.pop('password', None)
        dynamic_fields = serializer.validated_data.pop('dynamic_fields', None)
        location = serializer.validated_data.pop('location', None)
        groups = serializer.validated_data.pop('groups', None)
        # Get user by email and update or create
        user = User.objects.filter(email=email).first()
        if user:
            serializer.instance = user
            user = serializer.save()
        else:
            # Overwrite username with ID
            user = serializer.save(username=str(random.randint(100000000000, 999999999999)))
            user.username = user.id
            user.save(update_fields=['username'])
        if password is not None:
            user.set_password(password)
            user.save(update_fields=['password'])

        # sanity check, retrieve the user's profile (will create it if it doesnt exist)
        if not hasattr(user, 'cosinnus_profile') or not user.cosinnus_profile:
            get_user_profile_model()._default_manager.get_for_user(user)

        # Set dynamic_fields
        if dynamic_fields is not None:
            profile = user.cosinnus_profile
            profile.dynamic_fields = dynamic_fields
            profile.save()

        # Set location
        if location is not None:
            tag_object = user.cosinnus_profile.media_tag
            tag_object.location = location
            tag_object.save()

        # Create group memberships
        if groups is not None:
            # Get existing memberships
            old_groups = CosinnusGroupMembership.objects.filter(user=user, group__slug__in=groups)
            old_groups = old_groups.filter(status__in=MEMBER_STATUS)
            old_groups = old_groups.values_list('group__slug', flat=True)
            # Delete all other memberships
            CosinnusGroupMembership.objects.filter(user=user).exclude(group__slug__in=old_groups).delete()
            # Create new memberships
            new_groups = set(groups) - set(old_groups)
            for slug in new_groups:
                group = CosinnusGroup.objects.filter(slug=slug).first()
                if group:
                    CosinnusGroupMembership.objects.create(user=user, group=group,
                                                           status=MEMBERSHIP_MEMBER)



class OAuthUserView(APIView):
    """
    Used by Oauth2 authentication (Rocket.Chat) to retrieve user details
    """

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            avatar_url = user.cosinnus_profile.get_avatar_thumbnail_url(size=(200, 200)) if user.cosinnus_profile.avatar else ""
            if avatar_url:
                avatar_url = request.build_absolute_uri(avatar_url)
            # collect user groups
            
            membership_type_map = {
                MEMBERSHIP_ADMIN: 'admins',
                MEMBERSHIP_MANAGER: 'managers',
                MEMBERSHIP_MEMBER: 'users',
            }
            group_dict = {}
            group_url_dict = {}
            for group in user.cosinnus_profile.cosinnus_groups:
                # add a {group_id --> membership type} entry for each group the user is a member of
                membership = group.memberships.filter(user=user)[0]
                membership_type = membership_type_map.get(membership.status, None)
                if membership_type:
                    group_dict.update({
                        str(group.id): membership_type,
                    })
                # add a {group_id --> group_url} entry for each group the user is a member of
                group_url_dict.update({
                    str(group.id): group.get_absolute_url(),
                })
            
            return Response({
                'success': True,
                'id': user.username if user.username.isdigit() else str(user.id),
                'email': user.cosinnus_profile.rocket_user_email, # use the rocket user email (may be a non-verified fake one)
                'name': user.get_full_name(),
                'avatar': avatar_url,
                'group': group_dict,
                'group_urls': group_url_dict,
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
