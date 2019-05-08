# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect

from django.template.defaultfilters import date as django_date_filter

from cosinnus.models.group import CosinnusGroup
from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils.group import get_cosinnus_group_model

import logging
from cosinnus.models.idea import CosinnusIdea
from django.urls.base import reverse

logger = logging.getLogger('cosinnus')



class DashboardItem(dict):
    
    icon = None
    text = None
    url = None
    subtext = None
    is_emphasized = False
    
    def __init__(self, obj=None, is_emphasized=False, user=None):
        if obj:
            if is_emphasized:
                self['is_emphasized'] = is_emphasized
            # smart conversion by known models
            if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
                self['icon'] = 'fa-sitemap' if obj.type == CosinnusGroup.TYPE_SOCIETY else 'fa-group'
                self['text'] = obj.name
                self['url'] = obj.get_absolute_url()
            elif type(obj) is CosinnusIdea:
                self['icon'] = 'fa-lightbulb-o'
                self['text'] = obj.title
                self['url'] = obj.get_absolute_url()
            elif obj._meta.model.__name__ == 'Message':
                self['icon'] = 'fa-envelope'
                self['text'] = obj.subject
                self['url'] = reverse('postman:view_conversation', kwargs={'thread_id': obj.thread_id}) if obj.thread_id else obj.get_absolute_url()
                self['subtext'] = ', '.join([full_name(participant) for participant in obj.other_participants(user)])
            elif BaseTaggableObjectModel in inspect.getmro(obj.__class__):
                self['icon'] = 'fa-question'
                self['text'] = obj.title
                self['url'] = obj.get_absolute_url()
                self['subtext'] = obj.group.name
                if obj.__class__.__name__ == 'Event':
                    if obj.state == 2:
                        self['icon'] = 'fa-calendar-check-o'
                    else:
                        self['subtext'] = {'is_date': True, 'date': django_date_filter(obj.from_date, 'Y-m-d')}
                        self['icon'] = 'fa-calendar'
                if obj.__class__.__name__ == 'Etherpad':
                    self['icon'] = 'fa-file-text'
                if obj.__class__.__name__ == 'Ethercalc':
                    self['icon'] = 'fa-table'
                if obj.__class__.__name__ == 'FileEntry':
                    self['icon'] = 'fa-file'
                if obj.__class__.__name__ == 'Message':
                    self['icon'] = 'fa-envelope'
                if obj.__class__.__name__ == 'TodoEntry':
                    self['icon'] = 'fa-tasks'
                if obj.__class__.__name__ == 'Poll':
                    self['icon'] = 'fa-bar-chart'

