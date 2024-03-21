# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path

from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.views import select2

app_name = 'select2'

urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    urlpatterns += [
        path(f'{url_key}/<str:group>/members/', select2.group_members, name=prefix+'group-members'),
    ]

# IMPORTANT: this must be the last URLs matched, otherwise they will cover the group-specific ones
urlpatterns += [
    path('members/', select2.all_members, name='all-members'),
    path('members/managed-tags/<slug:tag_slug>/', select2.managed_tagged_members, name='managed-tag-members'),
    path('tags/', select2.tags_view, name='tags'),
    path('freetext_choices/<str:field_name>/', select2.dynamic_freetext_choices_view, name='dynamic-freetext-choices'),
    path('groups/', select2.groups_view, name='groups'),
]