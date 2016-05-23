# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django import template

register = template.Library()
logger = logging.getLogger('cosinnus')



@register.filter
def user_has_group_fb_page_access(user, group):
    """
    Check for a user and a group linked to a facebook page, if in that user's profile settings a Facebook page access token
    for the linked page is saved.
    """
    if not group.facebook_page_id:
        return False
    page_settings_key = 'fb_page_%(group_id)d_%(page_id)s' % {'group_id': group.id, 'page_id': group.facebook_page_id}
    return bool(user.cosinnus_profile.settings.get(page_settings_key, False))



