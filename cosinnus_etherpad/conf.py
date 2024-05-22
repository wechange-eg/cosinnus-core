# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from appconf import AppConf
from django.conf import settings  # noqa


class CosinnusEtherpadConf(AppConf):
    API_KEY = None
    BASE_URL = None
    PREFIX_TITLE = 'Etherpad: '
    FILE_PATH = '/etherpad'
    ENABLE_ETHERCALC = False
    ETHERCALC_BASE_URL = None
