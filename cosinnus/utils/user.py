# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib.auth.models import Group
from django.conf import settings

from cosinnus.core.registries.widgets import widget_registry
from cosinnus.models.widget import WidgetConfig
from cosinnus.models.group import CosinnusGroupMembership, MEMBERSHIP_MEMBER
from cosinnus.utils.group import get_cosinnus_group_model

logger = logging.getLogger('cosinnus')

def ensure_user_widget(user, app_name, widget_name, config={}):
    """ Makes sure if a widget exists for the given user, and if not, creates it """
    wqs = WidgetConfig.objects.filter(user_id=user.pk, app_name=app_name, widget_name=widget_name)
    if wqs.count() <= 0:
        widget_class = widget_registry.get(app_name, widget_name)
        widget = widget_class.create(None, group=None, user=user)
        widget.save_config(config)

    
def assign_user_to_default_auth_group(sender, **kwargs):
    user = kwargs.get('instance')
    for group_name in getattr(settings, 'NEWW_DEFAULT_USER_AUTH_GROUPS', []):
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        group.user_set.add(user)
        
def ensure_user_to_default_portal_groups(sender, created, **kwargs):
    """ Whenever a portal membership changes, make sure the user is in the default groups for this Portal """
    try:
        membership = kwargs.get('instance')
        CosinnusGroup = get_cosinnus_group_model()
        for group_slug in getattr(settings, 'NEWW_DEFAULT_USER_GROUPS', []):
            try:
                group = CosinnusGroup.objects.get(slug=group_slug, portal_id=membership.group.id)
                CosinnusGroupMembership.objects.get_or_create(user=membership.user, group=group, defaults={'status': MEMBERSHIP_MEMBER})
            except CosinnusGroup.DoesNotExist:
                continue
            
    except:
        # We fail silently, because we never want to 500 here unexpectedly
        logger.error("Error while trying to add User Membership for newly created user.")

