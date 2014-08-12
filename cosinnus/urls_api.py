# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.conf import settings
from cosinnus.utils.urls import api_patterns


urlpatterns = api_patterns(1, None, False, 'cosinnus.views',
    url(r'^login/$', 'user.login_api', name='login'),
    url(r'^logout/$', 'user.logout_api', name='logout'),

    url(r'^%s/list/$' % settings.COSINNUS_GROUP_URL_PATH,
        'group.group_list_api',
        name='group-list'),

    url(r'^%s/list/(?P<group>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH,
        'group.group_detail_api',
        name='group-detail'),

    url(r'^%s/add/$' % settings.COSINNUS_GROUP_URL_PATH,
        'group.group_create_api',
        name='group-add'),

    url(r'^%s/delete/(?P<group>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH,
        'group.group_delete_api',
        name='group-delete'),

    url(r'^%s/update/(?P<group>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH,
        'group.group_update_api',
        name='group-edit'),
                           
    url(r'^taggable_object/update/$',
        'api.taggable_object_update_api',
        name='taggable-object-update-api'),
                           
                           
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
