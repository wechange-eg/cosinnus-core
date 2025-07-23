# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

import cosinnus.api.views.mitwirkomat as mitwirkomat_views
import cosinnus.api.views.portal as portal_views
from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.utils.url_patterns import api_patterns
from cosinnus.views import common, group, user

urlpatterns = api_patterns(
    1,
    None,
    False,
    re_path(r'^statistics/general/$', portal_views.StatisticsView.as_view(), name='statistics-general'),
    re_path(
        r'^statistics/general/group_storage_info/',
        portal_views.SimpleStatisticsGroupStorageReportView.as_view(),
        name='statistics-group-storage-info',
    ),
    re_path(
        r'^statistics/general/conference_storage_info/',
        portal_views.SimpleStatisticsConferenceStorageReportView.as_view(),
        name='statistics-conference-storage-info',
    ),
    re_path(
        r'^statistics/general/project_storage_info/',
        portal_views.SimpleStatisticsProjectStorageReportView.as_view(),
        name='statistics-project-storage-info',
    ),
    re_path(
        r'^statistics/general/user_activity_info/',
        portal_views.SimpleStatisticsUserActivityInfoView.as_view(),
        name='user-activity-info',
    ),
    re_path(
        r'^statistics/general/user_activity_timeline/',
        portal_views.SimpleStatisticsUserActivityTimelineView.as_view(),
        name='user-activity-timeline',
    ),
    re_path(
        r'^statistics/general/bbb_room_visits/',
        portal_views.SimpleStatisticsBBBRoomVisitsView.as_view(),
        name='bbb-room-visits',
    ),
    re_path(
        r'^statistics/general/managed_tag/(?P<slug>[^/]+)/$',
        portal_views.StatisticsManagedTagFilteredView.as_view(),
        name='statistics-general-managed-tags',
    ),
    re_path(r'^user/me/$', user.user_api_me, name='user-api-me'),
    re_path(r'^common/get-metadata/$', common.get_metadata_from_url, name='api-get-metadata'),
)

if settings.COSINNUS_ENABLE_ADMIN_USER_DOMAIN_INFO_CSV_DOWNLOADS:
    urlpatterns += api_patterns(
        1,
        None,
        False,
        re_path(
            r'^statistics/general/user_domain_info/',
            portal_views.SimpleStatisticsUserDomainInfoView.as_view(),
            name='user-domain-info',
        ),
    )

if settings.COSINNUS_MITWIRKOMAT_INTEGRATION_ENABLED:
    urlpatterns += api_patterns(
        1,
        None,
        False,
        re_path(
            r'^mitwirkomat/export/',
            mitwirkomat_views.MitwirkomatExportView.as_view(),
            name='mitwirkomat-export',
        ),
    )

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')

    urlpatterns += api_patterns(
        1,
        None,
        False,
        re_path(r'^%s/list/$' % url_key, group.group_list_api, name=prefix + 'group-list'),
        re_path(r'^%s/list/(?P<group>[^/]+)/$' % url_key, group.group_detail_api, name=prefix + 'group-detail'),
        re_path(r'^%s/add/$' % url_key, group.group_create_api, name=prefix + 'group-add'),
        re_path(r'^%s/delete/(?P<group>[^/]+)/$' % url_key, group.group_delete_api, name=prefix + 'group-delete'),
        re_path(r'^%s/update/(?P<group>[^/]+)/$' % url_key, group.group_update_api, name=prefix + 'group-edit'),
    )

urlpatterns += api_patterns(
    1,
    None,
    True,
    re_path(r'^user/list/$', group.group_user_list_api, name='group-user-list'),
    re_path(r'^user/add/$', group.group_user_add_api, name='group-user-add'),
    re_path(r'^user/delete/(?P<username>[^/]+)/$', group.group_user_delete_api, name='group-user-delete'),
    re_path(r'^user/update/(?P<username>[^/]+)/$', group.group_user_update_api, name='group-user-edit'),
)
