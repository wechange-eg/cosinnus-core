# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus_conference import views

app_name = 'conference'

cosinnus_group_patterns = [
    url(r'^$', views.conference_redirect, name='conference'),
    url(r'^lobby/$', views.conference_lobby, name='conference-lobby'),
    url(r'^stage/$', views.conference_stage, name='conference-stage'),
    url(r'^discussions/$', views.conference_discussions, name='conference-discussions'),
    url(r'^workshops/$', views.conference_workshops, name='conference-workshops'),
    url(r'^coffee-tables/$', views.conference_coffee_tables, name='conference-coffee'),
    url(r'^networking/$', views.conference_networking, name='conference-networking'),
    url(r'^exhibition/$', views.conference_exhibition, name='conference-exhibition'),
]

cosinnus_root_patterns = []
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
