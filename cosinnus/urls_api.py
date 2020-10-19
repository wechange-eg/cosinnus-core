# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.conf import settings
from cosinnus.utils.url_patterns import api_patterns
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.views import group, user, common
from cosinnus.api.views import StatisticsView, StatisticsManagedTagFilteredView


urlpatterns = api_patterns(1, None, False,
    url(r'^login/$', user.login_api, name='login'),
    url(r'^logout/$', user.logout_api, name='logout'),
    
    url(r'^statistics/general/$', StatisticsView.as_view(),  name='statistics-general'),
    url(r'^statistics/general/managed_tag/(?P<slug>[^/]+)/$', StatisticsManagedTagFilteredView.as_view(),  name='statistics-general-managed-tags'),
    url(r'^user/me/$', user.user_api_me,  name='user-api-me'),
    url(r'^common/get-metadata/$', common.get_metadata_from_url,  name='api-get-metadata'),
)


for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    
    urlpatterns += api_patterns(1, None, False,
        url(r'^%s/list/$' % url_key, group.group_list_api, name=prefix+'group-list'),
        url(r'^%s/list/(?P<group>[^/]+)/$' % url_key, group.group_detail_api, name=prefix+'group-detail'),
        url(r'^%s/add/$' % url_key, group.group_create_api, name=prefix+'group-add'),
        url(r'^%s/delete/(?P<group>[^/]+)/$' % url_key, group.group_delete_api, name=prefix+'group-delete'),
        url(r'^%s/update/(?P<group>[^/]+)/$' % url_key, group.group_update_api, name=prefix+'group-edit'),
    )

urlpatterns += api_patterns(1, None, True,
    url(r'^user/list/$', group.group_user_list_api, name='group-user-list'),
    url(r'^user/add/$', group.group_user_add_api, name='group-user-add'),
    url(r'^user/delete/(?P<username>[^/]+)/$', group.group_user_delete_api, name='group-user-delete'),
    url(r'^user/update/(?P<username>[^/]+)/$', group.group_user_update_api,  name='group-user-edit'),
)
