# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.conf import settings as SETTINGS


def settings(request):

    return {
        'SETTINGS': SETTINGS,
    }
