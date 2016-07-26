# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django import template

from cosinnus.conf import settings

register = template.Library()


def get_map_marker_icon_settings():
    return getattr(settings, 'COSINNUS_MAP_MARKER_ICONS', {}) 

def get_map_marker_icon_settings_json():
    return json.dumps(get_map_marker_icon_settings())
    

@register.simple_tag()
def render_map_marker_icon_json():
    return get_map_marker_icon_settings_json()

