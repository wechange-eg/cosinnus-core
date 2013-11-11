# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

from appconf import AppConf


class CosinnusConf(AppConf):
    USER_PROFILE_MODEL = "cosinnus.UserProfile"
