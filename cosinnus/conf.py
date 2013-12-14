# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


class CosinnusConf(AppConf):
    ATTACHABLE_OBJECTS = {}
    GROUP_CACHE_TIMEOUT = 60 * 60 * 24
    TAG_OBJECT_MODEL = 'cosinnus.TagObject'
    USER_PROFILE_MODEL = 'cosinnus.UserProfile'
