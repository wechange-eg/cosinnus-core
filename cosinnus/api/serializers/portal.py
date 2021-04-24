# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django.contrib.staticfiles.templatetags.staticfiles import static
from rest_framework import serializers
from cosinnus.models import CosinnusPortal


__all__ = ('PortalSettingsSerializer',)


class PortalSettingsSerializer(serializers.ModelSerializer):
    logo_image = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusPortal
        fields = ('name', 'background_image', 'logo_image', 'top_color', 'bottom_color', 'extra_css')

    def get_logo_image(self, obj):
        return static('img/v2_navbar_brand.png')
