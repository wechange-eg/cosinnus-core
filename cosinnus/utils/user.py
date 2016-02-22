# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib.auth.models import Group
from django.conf import settings

from cosinnus.core.registries.widgets import widget_registry
from cosinnus.models.widget import WidgetConfig
from cosinnus.models.group import CosinnusGroupMembership, MEMBERSHIP_MEMBER
from cosinnus.utils.group import get_cosinnus_group_model
from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned

logger = logging.getLogger('cosinnus')

USER_MODEL = get_user_model()


def get_user_by_email_safe(email):
    """ Gets a user by email from the DB. Works around the fact that we're using a non-unique email
        field, but assume it should be unique.
        
        This method DOES NOT throw USER_MODEL.DoesNotExist! If no user was found, it returns None instead!
        
        If a user with the same 2 (case-insensitive) email addresses is found, we:
            - keep the user with the most recent login date and lowercase his email-address
            - set the older users inactive and change their email to '__deduplicate__<old-email>'
            
        @return: None if no user was found. A user object if found, even if it had a duplicated email.
    """
    if not email:
        return None
    try:
        user = USER_MODEL.objects.get(email__iexact=email)
        return user
    except MultipleObjectsReturned:
        users = USER_MODEL.objects.filter(email__iexact=email)
        # if none of the users has logged in, take the newest registered
        if users.filter(last_login__isnull=False).count() == 1:
            newest = users.latest('date_joined')
        else:
            newest = users.filter(last_login__isnull=False).latest('last_login')
        others = users.exclude(id=newest.id)
        
        newest.email = newest.email.lower()
        newest.save()
        
        for user in others:
            user.is_active = False
            user.email = '__deduplicate__%s' % user.email
            user.save()
            
        # we re-retrieve the newest user here so we can fail early here if something went really wrong
        return USER_MODEL.objects.get(email__iexact=email)
    
    except USER_MODEL.DoesNotExist:
        return None
        
        
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

