# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.tests.util_tests.views import some_view
from cosinnus.utils.url_patterns import api_patterns


urlpatterns = api_patterns(1, 'myapp', True,
    url(r'^some/view/$', some_view, name='view'),
)
