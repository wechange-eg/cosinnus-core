# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.views import select2

app_name = 'select2'

urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    urlpatterns += [
        url(r'%s/(?P<group>[^/]+)/members/$' % url_key, select2.group_members, name=prefix+'group-members'),
    ]

# IMPORTANT: this must be the last URLs matched, otherwise they will cover the group-specific ones
urlpatterns += [
    url(r'members/$', select2.all_members, name='all-members'),
    url(r'members/managed-tags/(?P<tag_slug>[^/]+)/$', select2.managed_tagged_members, name='managed-tag-members'), 
    url(r'tags/$', select2.tags_view, name='tags'),
    url(r'freetext_choices/(?P<field_name>[^/]+)/$', select2.dynamic_freetext_choices_view, name='dynamic-freetext-choices'),
    url(r'groups/$', select2.groups_view, name='groups'),
]