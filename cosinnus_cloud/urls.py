# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path, re_path

from cosinnus_cloud import views

app_name = 'cloud'

cosinnus_root_patterns = [
    path('cloud/oauth2/profile/', views.oauth_view, name='cloud-oath2-profile'),
]

cosinnus_group_patterns = [
    re_path(r'^stub/$', views.cloud_stub_view, name='stub'),
    # Deprecated URL, do not assign any more! Use `cloud-oath2-profile` under `/cloud/oauth2/profile/` instead!
    re_path(r'^oauth2/$', views.oauth_view, name='oauth2'),
    re_path(r'^$', views.cloud_index_view, name='index'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
