# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path, path
from cosinnus_message.views import *

app_name = 'message'

if settings.COSINNUS_ROCKET_ENABLED:
    cosinnus_root_patterns = [
        path('messages/', RocketChatIndexView.as_view(), name='message-global'),
        path('messages/write/<str:username>/', RocketChatWriteView.as_view(), name='message-write'),
        path('messages/write/group/<slug:slug>/', RocketChatWriteGroupView.as_view(), name='message-write-group'),
        path('messages/write/group/<slug:slug>/compose/', RocketChatWriteGroupComposeView.as_view(), name='message-write-group-compose'),
    ]
    cosinnus_group_patterns = []
else:
    cosinnus_root_patterns = []
    cosinnus_group_patterns = [
        re_path(r'^$', index, name='index'),
        # this doesn't work as a redirect to root
        #re_path(r'^$', RedirectView.as_view(url='/posteingang/')),
    ]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
