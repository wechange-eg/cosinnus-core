# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal
from cosinnus_stream import views

app_name = 'stream'

# user management not allowed in integrated mode
if not is_integrated_portal():
    cosinnus_root_patterns = [
        url(r'^activities/create/$', views.stream_create, name='create_stream'),
        url(r'^activities/all/', views.stream_detail, name='stream_public', kwargs={'is_all_portals': True}),
        url(r'^activities/(?P<slug>[^/]+)/$', views.stream_detail, name='stream'),
        url(r'^activities/(?P<slug>[^/]+)/edit/$', views.stream_update, name='edit_stream'),
        url(r'^activities/(?P<slug>[^/]+)/delete/$', views.stream_delete, name='delete_stream'),
        url(r'^activities/$', views.stream_detail, name='my_stream'),
    ]
else:
    cosinnus_root_patterns = []

cosinnus_group_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
