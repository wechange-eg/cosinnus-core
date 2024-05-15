# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from appconf import AppConf
from django.conf import settings  # noqa
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy as p_


class CosinnusTodoConf(AppConf):
    prefix = 'COSINNUS_TODO'

    DEFAULT_TODOLIST_TITLE = p_('Name of the default todo list for each group/project', 'General')

    DEFAULT_TODOLIST_SLUG = 'general'
