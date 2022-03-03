# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.utils.url_patterns import api_patterns


urlpatterns = api_patterns(1, None, True, 'tests.util_tests.views',
    url(r'^some/view/$', 'some_view', name='view'),
)
