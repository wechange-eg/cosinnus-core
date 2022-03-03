# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from cosinnus_cloud import views

app_name = "cloud"

cosinnus_root_patterns = []

cosinnus_group_patterns = [
    url(r"^stub/$", views.cloud_stub_view, name="stub"),
    url(r"^oauth2/$", views.oauth_view, name="oauth2"),
    url(r"^$", views.cloud_index_view, name="index"),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
