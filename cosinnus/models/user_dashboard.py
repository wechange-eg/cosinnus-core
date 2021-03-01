# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import logging
from cosinnus.models.cloud import NextcloudFileProxy

from django.template.defaultfilters import date as django_date_filter

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus.utils.group import get_cosinnus_group_model, \
    get_default_user_group_slugs

import logging
from cosinnus.models.idea import CosinnusIdea
from django.urls.base import reverse
from cosinnus.models.profile import BaseUserProfile
from django.utils.html import escape
from cosinnus_organization.models import CosinnusOrganization

logger = logging.getLogger('cosinnus')


class DashboardItem(dict):
    
    icon = None
    text = None
    url = None
    subtext = None
    is_emphasized = False
    group = None # group name of item if it has one
    group_icon = None # group type icon

    def __init__(self, obj=None, is_emphasized=False, user=None):
        if obj:
            from cosinnus.templatetags.cosinnus_tags import full_name
            if is_emphasized:
                self['is_emphasized'] = is_emphasized
            # smart conversion by known models
            if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
                self['icon'] = obj.get_icon()
                self['text'] = escape(obj.name)
                self['url'] = obj.get_absolute_url()
            elif type(obj) is CosinnusIdea:
                self['icon'] = obj.get_icon()
                self['text'] = escape(obj.title)
                self['url'] = obj.get_absolute_url()
            elif type(obj) is CosinnusOrganization:
                self['icon'] = 'fa-building'
                self['text'] = escape(obj.name)
                self['url'] = obj.get_absolute_url()
            elif isinstance(obj, NextcloudFileProxy):
                self['icon'] = 'fa-cloud'
                self['text'] = obj.name
                self['url'] = obj.url
                self['subtext'] = obj.excerpt
            elif obj._meta.model.__name__ == 'Message' and not settings.COSINNUS_ROCKET_ENABLED and not 'cosinnus_message' in settings.COSINNUS_DISABLED_COSINNUS_APPS:
                self['icon'] = 'fa-envelope'
                self['text'] = escape(obj.subject)
                self['url'] = reverse('postman:view_conversation', kwargs={'thread_id': obj.thread_id}) if obj.thread_id else obj.get_absolute_url()
                self['subtext'] = escape(', '.join([full_name(participant) for participant in obj.other_participants(user)]))
            elif issubclass(obj.__class__, BaseUserProfile):
                self['icon'] = obj.get_icon()
                self['text'] = escape(full_name(obj.user))
                self['url'] = obj.get_absolute_url()
            elif BaseTaggableObjectModel in inspect.getmro(obj.__class__):
                
                
                self['icon'] = 'fa-question'
                self['text'] = escape(obj.get_readable_title())
                self['url'] = obj.get_absolute_url()
                self['subtext'] = escape(obj.group.name)

                if hasattr(obj, 'get_icon'):
                    self['icon'] = obj.get_icon()
                if obj.group.slug in get_default_user_group_slugs():
                    self['group'] = escape(CosinnusPortal.get_current().name)
                else:
                    self['group'] = escape(obj.group.name)
                    self['group_icon'] = obj.group.get_icon()
                if obj.__class__.__name__ == 'Event':
                    if obj.state != 2:
                        self['subtext'] = {'is_date': True, 'date': django_date_filter(obj.from_date, 'Y-m-d')}
