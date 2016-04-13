# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry

urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    urlpatterns += patterns('cosinnus.views.select2',
        url(r'%s/(?P<group>[^/]+)/members/$' % url_key, 'group_members', name=prefix+'group-members'),
    )

# IMPORTANT: this must be the last URLs matched, otherwise they will cover the group-specific ones
urlpatterns += patterns('cosinnus.views.select2',
    url(r'members/$', 'all_members', name='all-members'),
    url(r'tags/$', 'tags_view', name='tags'),
    url(r'groups/$', 'groups_view', name='groups'),
)