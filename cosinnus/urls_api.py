# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.utils.urls import api_patterns


urlpatterns = api_patterns(1, None, False, 'cosinnus.views',
    url(r'^group/list/$',
        'group.group_list_api',
        name='group-list'),

    url(r'^group/list/(?P<group>[^/]+)/$',
        'group.group_detail_api',
        name='group-detail'),

    url(r'^group/add/$',
        'group.group_create_api',
        name='group-add'),

    url(r'^group/delete/(?P<group>[^/]+)/$',
        'group.group_delete_api',
        name='group-delete'),

    url(r'^group/update/(?P<group>[^/]+)/$',
        'group.group_update_api',
        name='group-edit'),
)

urlpatterns += api_patterns(1, None, True, 'cosinnus.views',
    url(r'^user/list/$',
        'group.group_user_list_api',
        name='group-user-list'),

    url(r'^user/add/$',
        'group.group_user_add_api',
        name='group-user-add'),

    url(r'^user/delete/(?P<username>[^/]+)/$',
        'group.group_user_delete_api',
        name='group-user-delete'),

    url(r'^user/update/(?P<username>[^/]+)/$',
        'group.group_user_update_api',
        name='group-user-edit'),
)
