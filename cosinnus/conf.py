# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa

from appconf import AppConf


class CosinnusConf(AppConf):
    ATTACHABLE_OBJECTS = {}
    GROUP_CACHE_TIMEOUT = 60 * 60 * 24
    TAG_OBJECT_MODEL = 'cosinnus.TagObject'
    USER_PROFILE_MODEL = 'cosinnus.UserProfile'

    # These are the default values for the bootstrap3-datetime picker and
    # are translated in `cosinnus/formats/LOCALE/formats.py`
    DATETIMEPICKER_DATETIME_FORMAT = 'YYYY-MM-DD HH:mm'
    DATETIMEPICKER_DATE_FORMAT = 'YYYY-MM-DD'
    DATETIMEPICKER_TIME_FORMAT = 'HH:mm'
