# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.api_frontend.views.user import LoginView, SignupView
from cosinnus.core.registries.group_models import group_model_registry


urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    # add project/group/conference-specific URLs like this
    urlpatterns += [
        #url(r'%s/(?P<group>[^/]+)/members/$' % url_key, select2.group_members, name=prefix+'group-members'),
    ]

urlpatterns += [
    url(r'^api/v3/login/', LoginView.as_view(), name='api-login'),
    url(r'^api/v3/signup/', SignupView.as_view(), name='api-signup'),
]