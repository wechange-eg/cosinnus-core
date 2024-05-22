# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from cosinnus.api.serializers.user import UserProfileSerializer
from cosinnus.tests.swappable_models.models import CustomUserProfile


class CustomUserProfileSerializer(UserProfileSerializer):
    dob = serializers.DateField(source='dob')

    class Meta(UserProfileSerializer.Meta):
        model = CustomUserProfile
        fields = UserProfileSerializer.Meta.fields + ('dob',)
