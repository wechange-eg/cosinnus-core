# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import logging
from cosinnus.models.cloud import NextcloudFileProxy

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus.utils.group import get_cosinnus_group_model, \
    get_default_user_group_slugs

from cosinnus.models import CosinnusPortal, get_domain_for_portal
from cosinnus.models.idea import CosinnusIdea
from django.urls.base import reverse
from cosinnus.models.profile import BaseUserProfile
from django.utils.html import escape
from cosinnus_organization.models import CosinnusOrganization

logger = logging.getLogger('cosinnus')


# a list of font-awesome class names that are not actual icons,
# useful for filtering them out of a class string
FONT_AWESOME_CLASS_FILTER = ['fa', 'fas', 'fa-fw', 'fa-2x', 'fa-3x', 'fa--spin', 'fa-cog']


class DashboardItem(dict):
    """
    Dictionary representation and API serializer of various cosinnus objects containing at least an icon, text and url.
    Is automatically initialized for the following objects: CosinnusGroup, CosinusIdea, CosinnusOrganization,
    NextcloudFileProxy, postman.Message, UserProfile and BaseTaggableObjectModel.
    Used by DashboardWidgets and in the v3 navigation API.
    """
    
    icon = None
    text = None
    url = None
    subtext = None
    is_emphasized = False
    group = None # group name of item if it has one
    group_icon = None # group type icon
    avatar = None

    def __init__(self, obj=None, is_emphasized=False, user=None):
        if obj:
            # Support for `TranslateableFieldsModelMixin
            if hasattr(obj, 'get_translated_readonly_instance'):
                obj = obj.get_translated_readonly_instance()
            
            from cosinnus.templatetags.cosinnus_tags import full_name
            if hasattr(obj, 'id'):
                self['id'] = f'{obj.__class__.__name__}{obj.id}'
            if is_emphasized:
                self['is_emphasized'] = is_emphasized
            # smart conversion by known models
            if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
                self['icon'] = obj.get_icon()
                self['text'] = escape(obj.name)
                self['url'] = obj.get_absolute_url()
                self['avatar'] = obj.avatar_url
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
                self['avatar'] = obj.avatar_url
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
                        date_dict = obj.get_date_or_now_starting_time()
                        if date_dict.get('is_date', False):
                            self['subtext'] = date_dict
                        else:
                            self['subtext'] = date_dict.get('date')

    def as_menu_item(self):
        image = self['avatar'] if 'avatar' in self else None
        id = self['id'] if 'id' in self else None
        return MenuItem(self['text'], self['url'], self['icon'], image, id=id)


class MenuItem(dict):
    """
    Dictionary used as a representation and API serializer of menu links consisting of a label, url, icon (optional),
    image-url (optional) and badge (optional). Used in the v3 navigation API.
    """

    def __init__(self, label, url=None, icon=None, image=None, badge=None, is_external=False, id=None):
        domain = get_domain_for_portal(CosinnusPortal.get_current())
        if not is_external and url and url.startswith(domain):
            url = url.replace(domain, '')
        self['id'] = id
        self['label'] = label
        self['url'] = url
        self['icon'] = icon
        self['is_external'] = is_external
        if image and image.startswith(domain):
            image = image.replace(domain, '')
        self['image'] = image
        self['badge'] = badge
