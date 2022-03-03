# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from cosinnus_message.views import *

app_name = 'message'

if settings.COSINNUS_ROCKET_ENABLED:
    cosinnus_root_patterns = [
        url(r'^messages/$', RocketChatIndexView.as_view(), name='message-global'),
        url(r'^messages/write/(?P<username>[^/]+)/$', RocketChatWriteView.as_view(), name='message-write'),
        url(r'^messages/write/group/(?P<slug>[^/]+)/$', RocketChatWriteGroupView.as_view(), name='message-write-group'),
    ]
    cosinnus_group_patterns = []
else:
    cosinnus_root_patterns = []
    cosinnus_group_patterns = [
        url(r'^$', index, name='index'),
        # this doesn't work as a redirect to root
        #url(r'^$', RedirectView.as_view(url='/posteingang/')),
    ]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
