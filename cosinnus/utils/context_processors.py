# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse

from cosinnus.conf import settings as SETTINGS


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
    return {
        'COSINNUS_BASE_URL': base_url,
    }
