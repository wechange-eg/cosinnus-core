# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import partial

from django.contrib.auth import get_user_model

from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.models.profile import UserProfile
from cosinnus.models.serializers.group import GroupSimpleSerializer


__all__ = ('UserProfileSerializer', 'UserDetailSerializer',
    'UserSimpleSerializer', )


class UserProfileSerializer(serializers.ModelSerializer):

    avatar = serializers.CharField(source="avatar_url")

    class Meta:
        model = UserProfile
        fields = ('id', 'avatar', )

    def __init__(self, *args, **kwargs):
        super(UserProfileSerializer, self).__init__(*args, **kwargs)

        def _transform_avatar_thubmnail(obj, value, size):
            return obj.get_avatar_thumbnail_url(size)

        for size in settings.COSINNUS_USER_PROFILE_AVATAR_THUMBNAIL_SIZES:
            size_read = '%dx%d' % size
            field = serializers.CharField(read_only=True, source="avatar_url")
            name = 'avatar_%s' % size_read
            self.fields[name] = field
            func = partial(_transform_avatar_thubmnail, size=size)
            setattr(self, 'transform_%s' % name, func)



class UserSimpleSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='get_username', read_only=True)
    profile = UserProfileSerializer(source='cosinnus_profile', many=False, read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'profile', )


class UserDetailSerializer(UserSimpleSerializer):

    cosinnus_groups = GroupSimpleSerializer(many=True, read_only=True)

    class Meta(UserSimpleSerializer.Meta):
        fields = UserSimpleSerializer.Meta.fields + ('cosinnus_groups', )
