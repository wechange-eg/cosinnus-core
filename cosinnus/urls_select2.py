# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns('cosinnus.views.select2',
    url(r'group/(?P<group>[^/]+)/members/$', 'group_members', name='group-members'),
    url(r'tags/$', 'tags_view', name='tags'),
)
