# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, include, url

from cosinnus.core.registries import url_registry


urlpatterns = patterns('',
    url(r'^', include('cosinnus.utils.django_auth_urls')),
    url(r'^', include('cosinnus.urls', namespace='cosinnus')),
    url(r'^', include(url_registry.api_urlpatterns, namespace='cosinnus-api')),
)
