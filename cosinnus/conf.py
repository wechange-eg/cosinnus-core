# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


class CosinnusConf(AppConf):
    TAG_OBJECT_MODEL = 'cosinnus.TagObject'
    USER_PROFILE_MODEL = 'cosinnus.UserProfile'
