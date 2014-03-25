# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model

from rest_framework import serializers

from cosinnus.models.profile import UserProfile
from cosinnus.models.serializers.group import GroupSimpleSerializer


__all__ = ('UserProfileSerializer', 'UserDetailSerializer',
    'UserSimpleSerializer', )


class UserProfileSerializer(serializers.ModelSerializer):

    avatar = serializers.CharField(source="avatar_url")

    class Meta:
        model = UserProfile
        fields = ('id', 'avatar', )


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
