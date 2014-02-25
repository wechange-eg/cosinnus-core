# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'^', include('cosinnus.utils.django_auth_urls')),
    url(r'^', include('cosinnus.urls', namespace='cosinnus')),
)
