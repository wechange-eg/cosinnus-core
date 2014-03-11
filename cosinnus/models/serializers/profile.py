# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model

from rest_framework import serializers

from cosinnus.models import BaseUserProfile


__all__ = ('BaseUserProfileSerializer', 'UserDetailSerializer',
    'UserSimpleSerializer', )


class BaseUserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = BaseUserProfile


class UserDetailSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='get_username', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'cosinnus_profile', 'cosinnus_groups')


class UserSimpleSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='get_username', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'username', )
