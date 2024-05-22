# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from cosinnus_cloud import views

app_name = 'cloud'

cosinnus_root_patterns = []

cosinnus_group_patterns = [
    re_path(r'^stub/$', views.cloud_stub_view, name='stub'),
    re_path(r'^oauth2/$', views.oauth_view, name='oauth2'),
    re_path(r'^$', views.cloud_index_view, name='index'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
