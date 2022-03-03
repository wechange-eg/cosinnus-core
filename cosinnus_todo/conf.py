# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa
from appconf import AppConf
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_


class CosinnusTodoConf(AppConf):
    
    prefix = 'COSINNUS_TODO'
    
    DEFAULT_TODOLIST_TITLE = p_('Name of the default todo list for each group/project', 'General')
    
    DEFAULT_TODOLIST_SLUG = 'general'
    
