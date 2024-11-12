# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django.templatetags.static import static
from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.models import CosinnusPortal

__all__ = ('PortalSettingsSerializer',)


class PortalSettingsSerializer(serializers.ModelSerializer):
    
    display_name = serializers.SerializerMethodField()
    logo_image = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusPortal
        fields = ('name', 'display_name', 'background_image', 'logo_image', 'top_color', 'bottom_color', 'extra_css')
    
    def get_display_name(self, obj):
        return settings.COSINNUS_BASE_PAGE_TITLE_TRANS
    
    def get_logo_image(self, obj):
        return static('img/v2_navbar_brand.png')
