# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from functools import partial

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from cosinnus.conf import settings
from cosinnus.models.membership import MEMBER_STATUS
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.import_utils import import_from_settings

User = get_user_model()

__all__ = (
    'UserProfileSerializer',
    'UserSerializer',
    'UserSerializerWithToken',
)


class UserProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(source='avatar_url')

    class Meta(object):
        model = get_user_profile_model()
        fields = ('id', 'avatar')

    def __init__(self, *args, **kwargs):
        super(UserProfileSerializer, self).__init__(*args, **kwargs)

        def _transform_avatar_thubmnail(obj, value, size):
            return obj.get_avatar_thumbnail_url(size)

        for size in settings.COSINNUS_USER_PROFILE_AVATAR_THUMBNAIL_SIZES:
            size_read = '%dx%d' % size
            field = serializers.CharField(read_only=True, source='avatar_url')
            name = 'avatar_%s' % size_read
            self.fields[name] = field
            func = partial(_transform_avatar_thubmnail, size=size)
            setattr(self, 'transform_%s' % name, func)


def get_user_profile_serializer():
    """
    Return the cosinnus user profile serializer that is defined in
    :data:`settings.COSINNUS_USER_PROFILE_SERIALIZER`
    """
    return import_from_settings('COSINNUS_USER_PROFILE_SERIALIZER')


_UserProfileSerializer = get_user_profile_serializer()


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='get_username', read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)

    profile = _UserProfileSerializer(source='cosinnus_profile', many=False, read_only=True)

    class Meta(object):
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'is_guest', 'profile')


class UserSerializerWithToken(TokenObtainPairSerializer):
    token = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True)

    def get_token(self, obj):
        token = super().get_token(obj)
        return token

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

    class Meta:
        model = User
        fields = ('token', 'username', 'password')


class ReadWriteSerializerMethodField(serializers.SerializerMethodField):
    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs['source'] = '*'
        super(serializers.SerializerMethodField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        return {self.field_name: data}


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    location = ReadWriteSerializerMethodField(required=False)
    dynamic_fields = ReadWriteSerializerMethodField(required=False)
    groups = ReadWriteSerializerMethodField(required=False)
    avatar = ReadWriteSerializerMethodField(required=False)

    class Meta(object):
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'password',
            'location',
            'dynamic_fields',
            'groups',
            'avatar',
        )

    def _sanity_check_userprofile(self, user):
        # sanity check, retrieve the user's profile (will create it if it doesnt exist)
        if not user.cosinnus_profile:
            get_user_profile_model()._default_manager.get_for_user(user)

    def get_location(self, obj):
        self._sanity_check_userprofile(obj)
        return obj.cosinnus_profile.media_tag.location or ''

    def get_dynamic_fields(self, obj):
        self._sanity_check_userprofile(obj)
        return obj.cosinnus_profile.dynamic_fields

    def get_groups(self, obj):
        queryset = obj.cosinnus_memberships.filter(status__in=MEMBER_STATUS)
        return list(queryset.values_list('group__slug', flat=True))

    def get_avatar(self, obj):
        self._sanity_check_userprofile(obj)
        return obj.cosinnus_profile.avatar_url
