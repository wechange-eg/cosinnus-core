# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from cosinnus.conf import settings

urlpatterns = patterns('cosinnus.views.select2',
    url(r'%s/(?P<group>[^/]+)/members/$' % settings.COSINNUS_GROUP_URL_PATH, 'group_members', name='group-members'),
    url(r'members/$', 'all_members', name='all-members'),
    url(r'tags/$', 'tags_view', name='tags'),
)
