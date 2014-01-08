# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse

from cosinnus.conf import settings


__all__ = ('JSONResponse', )


# Taken from bakery: https://github.com/muffins-on-dope/bakery
# License: BSD
# https://github.com/muffins-on-dope/bakery/blob/9bd3b6b93b/bakery/api/views.py
DUMPS_KWARGS = {
    'cls': DjangoJSONEncoder,
    'indent': True if settings.DEBUG else None
}


class JSONResponse(HttpResponse):

    def __init__(self, data):
        super(JSONResponse, self).__init__(
            json.dumps(data, **DUMPS_KWARGS),
            content_type='application/json'
        )
