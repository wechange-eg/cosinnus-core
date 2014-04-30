# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from cosinnus.models.serializers.profile import BaseUserProfileSerializer

from tests.swappable_models.models import CustomUserProfile


class CustomUserProfileSerializer(BaseUserProfileSerializer):

    dob = serializers.DateField(source="dob")

    class Meta(BaseUserProfileSerializer.Meta):
        model = CustomUserProfile
        fields = BaseUserProfileSerializer.Meta.fields + ('dob', )
