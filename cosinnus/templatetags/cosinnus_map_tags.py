# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django import template

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal

register = template.Library()


def get_map_marker_icon_settings():
    return getattr(settings, 'COSINNUS_MAP_MARKER_ICONS', {}) 

def get_map_marker_icon_settings_json():
    return json.dumps(get_map_marker_icon_settings())
    
@register.simple_tag()
def render_map_marker_icon_json():
    return get_map_marker_icon_settings_json()


def get_cosinnus_portal_info():
    """ Gets a dict of the most important portal infos by portal id """
    portals = CosinnusPortal.get_all()
    portal_info = {
        'current': CosinnusPortal.get_current().id,
    }
    for portal in portals:
        portal_info[portal.id] = {
            'name': portal.name,
            'domain': portal.get_domain(),
            'image_url': portal.get_logo_image_url(),
        }
    return portal_info
    
@register.simple_tag()
def render_cosinnus_portal_info_json():
    return json.dumps(get_cosinnus_portal_info())

