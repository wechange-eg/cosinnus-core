# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django import template
from django.utils.safestring import mark_safe

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal

register = template.Library()


def get_cosinnus_portal_info():
    """Gets a dict of the most important portal infos by portal id"""
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
    return mark_safe(json.dumps(get_cosinnus_portal_info()))
