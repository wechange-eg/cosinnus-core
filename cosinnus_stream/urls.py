# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path

from cosinnus.templatetags.cosinnus_tags import is_integrated_portal
from cosinnus_stream import views

app_name = 'stream'

# user management not allowed in integrated mode
if not is_integrated_portal():
    cosinnus_root_patterns = [
        path('activities/create/', views.stream_create, name='create_stream'),
        path('activities/all/', views.stream_detail, name='stream_public', kwargs={'is_all_portals': True}),
        path('activities/<slug:slug>/', views.stream_detail, name='stream'),
        path('activities/<slug:slug>/edit/', views.stream_update, name='edit_stream'),
        path('activities/<slug:slug>/delete/', views.stream_delete, name='delete_stream'),
        path('activities/', views.stream_detail, name='my_stream'),
    ]
else:
    cosinnus_root_patterns = []

cosinnus_group_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
