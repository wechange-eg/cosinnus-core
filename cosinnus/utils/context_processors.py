# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.utils.formats import get_format

from cosinnus.conf import settings as SETTINGS
from cosinnus.models.serializers.profile import UserSimpleSerializer
import json


def settings(request):
    return {
        'SETTINGS': SETTINGS,
    }


def cosinnus(request):
    base_url = '{scheme}{domain}{path}'.format(
        scheme=request.is_secure() and 'https://' or 'http://',
        domain=request.get_host(),
        path=reverse('cosinnus:index')
    )

    user = request.user
    if user.is_authenticated():
        user_json = json.dumps(UserSimpleSerializer(request.user).data)
    else:
        user_json = json.dumps(False)

    return {
        'COSINNUS_BASE_URL': base_url,
        'COSINNUS_USER': user_json,
        'COSINNUS_DATE_FORMAT': get_format('COSINNUS_DATETIMEPICKER_DATE_FORMAT'),
        'COSINNUS_DATETIME_FORMAT': get_format('COSINNUS_DATETIMEPICKER_DATETIME_FORMAT'),
        'COSINNUS_TIME_FORMAT': get_format('COSINNUS_DATETIMEPICKER_TIME_FORMAT'),
    }
