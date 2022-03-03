# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, url


urlpatterns = [
    url(r'^', include('cosinnus.utils.django_auth_urls')),
    url(r'^', include('cosinnus.urls', namespace='cosinnus')),
]
